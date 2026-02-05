#!/usr/bin/env python3
import sys
import subprocess
import statistics
import os
import csv

# Mappings for TLS handshake types and OpenVPN opcodes
HS_MAP = {
    '1': 'ClientHello',
    '2': 'ServerHello',
    '11': 'Finished',
    '14': 'ChangeCipherSpec',
}

CT_MAP = {'1': 'ChangeCipherSpec', 
          '22': 'Handshake', 
          '20': 'ChangeCipherSpec', 
          '23': 'ApplicationData'}

OP_MAP = {
    '0x07': 'P_CONTROL_HARD_RESET_CLIENT_V2',
    '0x08': 'P_CONTROL_HARD_RESET_SERVER_V2',
    '0x04': 'P_CONTROL_V1',
    '0x05': 'P_ACK_V1',
    '0x09': 'P_DATA_V2',
}

def ct_name(code):
    return CT_MAP.get(code, f'CT_{code}')


def hs_name(code):
    return HS_MAP.get(code, f'HS_{code}')

def op_name(code):
    return OP_MAP.get(code, f'OP_{code}')

#####################
# Función genérica para ejecutar tshark
#####################



def run_tshark(pcap, decode_as, display_filter, fields):
    """
    Executes tshark -r <pcap> [-d <decode_as>] [-Y <display_filter>] -T fields -e <fields>...
    Returns a list of rows, each row being a list of column values.
    """
    cmd = ['tshark', '-r', pcap]
    if decode_as:
        cmd += ['-d', decode_as]
    if display_filter:
        cmd += ['-Y', display_filter]
    cmd += ['-T', 'fields']
    for f in fields:
        cmd += ['-e', f]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print("Error running tshark:", p.stderr, file=sys.stderr)
        sys.exit(1)
    return [line.split('\t') for line in p.stdout.splitlines()]

###################
# Extracción de paquetes OpenVPN
###################


def extract_openvpn(pcap, port):
    """
    Extracts all OpenVPN packets on UDP/port that carry an opcode.
    Returns a list of tuples:
       (message_name, time_relative, length, session_id_hex, frame_number)
    """

    rows = run_tshark(
        pcap,
        f'udp.port=={port},openvpn',                  
        f'udp.port=={port} && openvpn.opcode && !icmp',
        [
            'frame.number',          
            'frame.time_relative',
            'openvpn.opcode',
            'frame.len',
            'openvpn.sessionid',
            'openvpn.peerid',
            'openvpn.rsessionid',
            'tls.record.content_type',
            'tls.handshake.type',
            'tls.record.opaque_type'
        ]
    )

    out = []

    for row in rows:
        # nos aseguramos de tener siempre 9 columnas
        if len(row) < 9:
            row = row + [''] * (8 - len(row))

        frame_no, t_str, op_hex, ln_str, sess_id, peerid, remote_id,tls_record, tls_hand_type, tls_Opaque_record  = row

        try:
            frame_no = int(frame_no)
            name = op_name(op_hex)
            t = float(t_str)
            ln = int(ln_str)

            # --- session_id  ---
            if sess_id:
                session_id = sess_id
            else:
                session_id = None

             # --- session_id  ---
            if remote_id:
                session_id_remote = remote_id
            else:
                session_id_remote = None    

            out.append((name, t, ln, session_id, frame_no, peerid, session_id_remote,tls_record, tls_hand_type,tls_Opaque_record))

        except Exception:
            continue

    return out


##############
# Filtrado de HARD RESET CLIENT V2 repetidos
# Si hay errores y se mandan variso HARD RESET CLIENT V2 seguidos con el mismo session_id,
# solo contamos el primero.
##############

def filter_hard_resest_repetidos (vpn):
    _pkt_filtered = []
    session_id = 0 
    count = 0

    for pkt in vpn:
        if pkt[0] == 'P_CONTROL_HARD_RESET_CLIENT_V2':
         #print("✅ Found P_CONTROL_HARD_RESET_CLIENT_V2",pkt[3])
         if (pkt[3] != session_id):
            _pkt_filtered.append(pkt)
            session_id = pkt[3]
            count += 1
        else :
           _pkt_filtered.append(pkt)   
              
    return _pkt_filtered

################
# Dump sessions to CSV
################

import csv

def dump_sessions(sessions_vpn, sessions_tls, sig ,kem):
    dmp_file = f"sessions_filtered_stats_handshakes_{sig}_{kem}.csv"

    with open(dmp_file, "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([
            "session_id",
            "session_start",
            "session_end",
            "session_duration_ms",
            "vpn_packet_count",
            "vpn_packet_sum",
            "vpn_packets",
            "vpn_frames",
            "tls_start",
            "tls_end",
            "tls_duration_ms",
            "tls_packet_count",
            "tls_packet_sum",
            "tls_packets",
            "tls_frames",
            "vpn_duration_ms",
            "tls_duration_ms",
            "check"
        ])
        
        for i, s in enumerate(sessions_vpn):
            start = s["start"]
            end = s["end"]
            sizes = s["sizes"]
            frames = s["frames"]

            duration = (end - start) * 1000 if end is not None else 0
            packet_count = len(sizes)
            packet_sum = sum(sizes)
            packets_str = " ".join(str(x) for x in sizes)
            frames_str = " ".join(str(x) for x in frames)

            tls_start = tls_end = tls_duration = ""
            tls_packet_count = tls_packet_sum = ""
            tls_packets_str = tls_frames_str = ""

            if sessions_tls is not None and i < len(sessions_tls):
                tls = sessions_tls[i]
                t_start = tls.get("start")
                t_end = tls.get("end")
                t_sizes = tls.get("sizes", [])
                t_frames = tls.get("frames", [])

                tls_start = t_start
                tls_end = t_end
                tls_duration = (t_end - t_start) * 1000 if (t_start is not None and t_end is not None) else 0
                tls_packet_count = len(t_sizes)
                tls_packet_sum = sum(t_sizes) if t_sizes else 0
                tls_packets_str = " ".join(str(x) for x in t_sizes)
                tls_frames_str = " ".join(str(x) for x in t_frames)

            writer.writerow([
                s["session_id"],
                start,
                end,
                duration,
                packet_count,
                packet_sum,
                packets_str,
                frames_str,
                tls_start,
                tls_end,
                tls_duration,
                tls_packet_count,
                tls_packet_sum,
                tls_packets_str,
                tls_frames_str,
                duration,
                tls_duration,
                "YES" if (
                    duration not in ("", None)
                    and tls_duration not in ("", None)
                    and float(duration) > float(tls_duration)
                ) else "NO"
            ])



###############
# Helper to check tls_opaque_record for ChangeCipherSpec (23)
###############

def has_tls_opaque(tls_opaque_record):
    """
    tls_opaque_record puede ser:
      - ""
      - "23"
      - "23,23"
      - "23,23,23"
    Devuelve True si contiene algún 23.
    """
    if not tls_opaque_record:
        return False

    # Si viene como string tipo "23,23"
    if isinstance(tls_opaque_record, str):
        try:
            vals = [int(x) for x in tls_opaque_record.split(',')]
            return 23 in vals
        except:
            return False

    # Si viene ya parseado como lista
    if isinstance(tls_opaque_record, (list, tuple)):
        return 23 in tls_opaque_record

    # Si viene como entero
    if isinstance(tls_opaque_record, int):
        return tls_opaque_record == 23

    return False

def stats(xs):
    """
    Returns:
      - mean (float)             → media de los datos (sin extremos)
      - coefficient of variation (float)
      - outlier_percent (float) → porcentaje de outliers (según Tukey)
    """

    sorted_xs = sorted(xs)

    # Trimmed mean (quita extremos si hay más de 2 elementos)
    trimmed = sorted_xs[1:-1] if len(sorted_xs) > 2 else sorted_xs
    mean = statistics.mean(trimmed)

    # CV (con todos los datos filtrados)
    cv = (statistics.stdev(xs) / mean) if len(trimmed) > 1 and mean != 0 else 0.0

    # Outliers usando Tukey
    q1 = statistics.quantiles(trimmed, n=4)[0]
    q3 = statistics.quantiles(trimmed, n=4)[2]
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = [x for x in trimmed if x < lower or x > upper]

    # Porcentaje de outliers
    outlier_percent = (len(outliers) / len(trimmed)) * 100

    return mean, cv, outlier_percent



####################
#########
# Main
#####################

def main():
    if len(sys.argv) not in (2, 3):
        print(f"Usage: {sys.argv[0]} <trace.pcapng> [vpn_port]")
        sys.exit(1)
    pcap = sys.argv[1]
    port = sys.argv[2] if len(sys.argv) == 3 else '1194'


    filename = os.path.basename(pcap)  # por ejemplo: ed25519-x25519.pcapng
    name, _ = os.path.splitext(filename)  # quita la extensión
    try:
        sig_alg, kem_alg = name.split('-')
    except ValueError:
        print(f"❌ Error: expected filename format <signature>-<kem>.pcapng, got '{filename}'")
        sys.exit(1)

    print(f"🔐 Signature Algorithm: {sig_alg}")
    print(f"🔑 KEM Algorithm      : {kem_alg}")

    # 1) Extract OpenVPN packets
    vpn_pkts = extract_openvpn(pcap, port)
    # 2) Filter repeated HARD RESET CLIENT V2
    filter_vpn =  filter_hard_resest_repetidos (vpn_pkts)
    
    #print(filter_vpn)
    print(f"🔍  OpenVPN filter / TOTAL packets on UDP/{port}: {len(filter_vpn)} / {len(vpn_pkts)}")
    
    if not vpn_pkts:
        print("No OpenVPN traffic detected on that port.")
        sys.exit(1)

    # 3) Segment into connections (start at CLIENT_V2, end at first P_DATA_V2)
    conns_vpn = []
    curr_vpn = None
    conns_tls = []
    curr_tls = None

    handshake_times = []
    vpn_times = []

    status = 0;
    for msg, t, sz, session_id, number, peer_id, remote_id, tls_record, tls_hand_type, tls_Opaque_record  in filter_vpn:
        
        if msg == 'P_CONTROL_HARD_RESET_CLIENT_V2':
            if curr_vpn:
                conns_vpn.append(curr_vpn)
                status = 0
            curr_vpn = {'start': t, 'sizes': [sz], 'end': None, 'session_id': session_id, 'frames': [number], 'session_id_remote': None}
            status = 1
        
        elif status==1 and msg == 'P_CONTROL_HARD_RESET_SERVER_V2':
            curr_vpn['session_id_remote'] = session_id
            status = 2
            curr_vpn['sizes'].append(sz)
            curr_vpn['frames'].append(number)

        elif curr_vpn and  status == 2 and msg == 'P_CONTROL_V1':
            curr_vpn['sizes'].append(sz)
            curr_vpn['frames'].append(number)
            
            name = ct_name(tls_record)
            type = hs_name(tls_hand_type)

            if tls_record == '22' and type == 'ClientHello': # Handshake ClientHello
                status = 3
                curr_tls = {'start': t, 'sizes': [sz], 'end': None, 'session_id': session_id, 'frames': [number], 'session_id_remote': None}
        
        elif curr_vpn and  status == 3 and msg == 'P_CONTROL_V1':
            curr_vpn['sizes'].append(sz)
            curr_vpn['frames'].append(number)
            
            name = ct_name(tls_record)
            type = hs_name(tls_hand_type)
                        
            if type == 'ServerHello': # Handshake ServerHello
                status = 4
                curr_tls['sizes'].append(sz)
                curr_tls['frames'].append(number)
              #  print("Server Hello detected. STATUS updated to 4. tls_record:",tls_record," tls_hand_type:",tls_hand_type,name, type, tls_Opaque_record)

        elif curr_vpn and status == 4 and msg == 'P_CONTROL_V1':
            curr_vpn['sizes'].append(sz)
            curr_vpn['frames'].append(number)

            if has_tls_opaque( tls_Opaque_record) : # Applocation Data ChangeCipherSpec
                curr_tls['sizes'].append(sz)
                curr_tls['frames'].append(number)

        elif curr_vpn and status == 4 and msg == 'P_ACK_V1':
            curr_vpn['sizes'].append(sz)
            curr_vpn['frames'].append(number)
            status = 5

            curr_tls['end'] = t
            conns_tls.append(curr_tls)
            dt_hs = (curr_tls['end'] - curr_tls['start']) 
            handshake_times.append(dt_hs)

            curr_tls = None
            

        elif curr_vpn and  status == 5 and msg == 'P_CONTROL_V1':
            curr_vpn['sizes'].append(sz)
            curr_vpn['frames'].append(number)
            
        elif curr_vpn and status == 5 and msg == 'P_ACK_V1':
            curr_vpn['sizes'].append(sz)
            curr_vpn['frames'].append(number)
            status = 6
        
        elif curr_vpn and  status == 6 and msg == 'P_CONTROL_V1':
            curr_vpn['sizes'].append(sz)
            curr_vpn['frames'].append(number)
            
        elif curr_vpn and status == 6 and msg == 'P_ACK_V1':
            curr_vpn['sizes'].append(sz)
            curr_vpn['frames'].append(number)
            status = 7

        elif curr_vpn and status >6 :
            curr_vpn['sizes'].append(sz)
            curr_vpn['frames'].append(number)

            if msg == 'P_DATA_V2' and curr_vpn['end'] is None: #len(curr_vpn['sizes']) > 14:
                curr_vpn['end'] = t
                conns_vpn.append(curr_vpn)

                dt_hs = (curr_vpn['end'] - curr_vpn['start']) 
                vpn_times.append(dt_hs)


                curr_vpn = None

    print(f"🔗 Total full VPN connections (control→data): {len(conns_vpn)}")
    if not conns_vpn:
        print("No full VPN connections (control→data) found.")
        sys.exit(1)
    
    dump_sessions(conns_vpn,conns_tls,sig_alg,kem_alg)

    print("📊 Statistics:")
    
    m_hs, cv_hs, out_hs = stats(handshake_times)
    m_vp, cv_vp, out_vp = stats(vpn_times)

    print(f"\n**********************************************\nAverage handshake time: {m_hs*1000:.2f} ms (CV={cv_hs:.2f}) (O={out_hs:.2f})")
    print(f"\nAverage VPN setup time: {m_vp*1000:.2f} ms (CV={cv_vp:.2f}) (O={out_vp:.2f})\n")

    # 6) Export CSV with handshake durations
    csv_file = f"{filename.replace('.pcapng','')}_handshakes.csv"
    with open(csv_file, 'w') as f:
        f.write(f"{kem_alg}\n")               # Second line as column header (KEM name)
        for val in handshake_times:
            f.write(f"{val*1000:.2f}\n")      # Values in milliseconds
    print(f"\n📁 Handshake durations saved to: {csv_file}")

    # 7) Export CSV with vpn durations
    csv_file = f"{filename.replace('.pcapng','')}_vpn.csv"
    with open(csv_file, 'w') as f:
        f.write(f"{kem_alg}\n")               # Second line as column header (KEM name)
        for val in vpn_times:
            f.write(f"{val*1000:.2f}\n")      # Values in milliseconds
    print(f"\n📁 VPN durations saved to: {csv_file}")

if __name__ == '__main__':
    main()