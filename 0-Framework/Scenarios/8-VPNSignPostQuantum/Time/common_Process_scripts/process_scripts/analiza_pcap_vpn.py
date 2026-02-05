#!/usr/bin/env python3
import sys
import subprocess
import statistics
import os

# Mappings for TLS handshake types and OpenVPN opcodes
HS_MAP = {
    '1': 'ClientHello',
    '2': 'ServerHello',
    '11': 'Finished',
    '14': 'ChangeCipherSpec',
}
OP_MAP = {
    '0x07': 'P_CONTROL_HARD_RESET_CLIENT_V2',
    '0x08': 'P_CONTROL_HARD_RESET_SERVER_V2',
    '0x04': 'P_CONTROL_V1',
    '0x05': 'P_ACK_V1',
    '0x09': 'P_DATA_V2',
}


tls_packet_count_reference = {
    ('ed25519', 'x25519'): 4,
    ('ed25519', 'x25519_mlkem512'): 4,
    ('ed25519', 'mlkem512'): 4,
    ('ed25519', 'x25519_hqc128'): 4,
    ('ed25519', 'hqc128'): 4,

    ('secp384r1', 'x448'): 4,
    ('secp384r1', 'x448_mlkem768'): 4,
    ('secp384r1', 'mlkem768'): 5,
    ('secp384r1', 'x448_hqc192'): 4,
    ('secp384r1', 'hqc192'): 4,

    ('secp521r1', 'P521'): 4,
    ('secp521r1', 'p521_mlkem1024'): 4,
    ('secp521r1', 'mlkem1024'): 4,
    ('secp521r1', 'p521_hqc256'): 4,
    ('secp521r1', 'hqc256'): 4,

    ('mldsa44', 'x25519'): 5,
    ('mldsa44', 'mlkem512'): 5,
    ('mldsa44', 'hqc128'): 6,

    ('mldsa65', 'x448'): 5,
    ('mldsa65', 'mlkem768'): 6,
    ('mldsa65', 'hqc192'): 5,

    ('mldsa87', 'P521'): 5,
    ('mldsa87', 'mlkem1024'): 5,
    ('mldsa87', 'hqc256'): 5

}

vpn_packet_count_reference = {
    ('ed25519', 'x25519'): 15,
    ('ed25519', 'x25519_mlkem512'): 15,
    ('ed25519', 'mlkem512'): 15,
    ('ed25519', 'x25519_hqc128'): 25,
    ('ed25519', 'hqc128'): 25,

    ('secp384r1', 'x448'): 16,
    ('secp384r1', 'x448_mlkem768'): 20,
    ('secp384r1', 'mlkem768'): 20,
    ('secp384r1', 'x448_hqc192'): 38,
    ('secp384r1', 'hqc192'): 38,

    ('secp521r1', 'P521'): 16,
    ('secp521r1', 'p521_mlkem1024'): 20,
    ('secp521r1', 'mlkem1024'): 20,
    ('secp521r1', 'p521_hqc256'): 52,
    ('secp521r1', 'hqc256'): 52,

    ('mldsa44', 'x25519'): 47,
    ('mldsa44', 'mlkem512'): 47,
    ('mldsa44', 'hqc128'): 57,

    ('mldsa65', 'x448'): 60,
    ('mldsa65', 'mlkem768'): 64,
    ('mldsa65', 'hqc192'): 84,

    ('mldsa87', 'P521'): 77,
    ('mldsa87', 'mlkem1024'): 83,
    ('mldsa87', 'hqc256'): 115


}

def hs_name(code):
    return HS_MAP.get(code, f'HS_{code}')

def op_name(code):
    return OP_MAP.get(code, f'OP_{code}')

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

def extract_openvpn(pcap, port):
    """
    Extracts all OpenVPN packets on UDP/port that carry an opcode.
    Returns a list of tuples (message_name, time_relative, length).
    """
    rows = run_tshark(
        pcap,
        f'udp.port=={port},openvpn',
        'openvpn.opcode',
        ['frame.time_relative', 'openvpn.opcode', 'frame.len']
    )
    out = []
    for t_str, op_hex, ln_str in rows:
        try:
            name = op_name(op_hex)
            t = float(t_str)
            ln = int(ln_str)
            out.append((name, t, ln))
        except:
            continue
    return out

def extract_tls(pcap, port, debug=False):
    """
    Extracts all TLS records encapsulated in OpenVPN on UDP/port.
    Returns a list of tuples (record_type, time_relative, length).
    """
    rows = run_tshark(
        pcap,
        f'udp.port=={port},openvpn',
        'tls.record',
        ['tls.record.content_type', 'frame.time_relative', 'frame.len']
    )
    out = []
    for hs_code, t_str, ln_str in rows:
        try:
            # Map content type to simplified name
            ct_map = {'1': 'ChangeCipherSpec', '22': 'Handshake', '20': 'ChangeCipherSpec', '23': 'ApplicationData'}
            name = ct_map.get(hs_code, f'ContentType_{hs_code}')
            t = float(t_str)
            ln = int(ln_str)
            if debug:
                print(f"DEBUG TLS record: hs_code={hs_code}, name={name}, time={t}, len={ln}")
            out.append((name, t, ln))
        except Exception as e:
            if debug:
                print(f"Skipping invalid row: {hs_code}, error: {e}")
            continue
    return out


def trimmed_mean(xs, pct=0.05):
    n = len(xs)
    k = int(n * pct)
    if n <= 2 * k:
        return statistics.mean(xs)  # No se puede recortar tanto
    trimmed = sorted(xs)[k:-k]
    return statistics.mean(trimmed)


def stats(xs):
    """
    Returns:
      - mean (float)             → media de los datos (sin extremos)
      - coefficient of variation (float)
      - outlier_percent (float) → porcentaje de outliers (según Tukey)
    Notes:
      - Descarta valores > 100 ms antes de cualquier cálculo
    """
    # Filtrar valores por debajo de 100 ms
    filtered = [x for x in xs if x <= 0.1]

    if len(filtered) < 2:
        return 0.0, 0.0, 0.0

    sorted_xs = sorted(filtered)

    # Trimmed mean (quita extremos si hay más de 2 elementos)
    trimmed = sorted_xs[1:-1] if len(sorted_xs) > 2 else sorted_xs
    mean = statistics.mean(trimmed)

    # CV (con todos los datos filtrados)
    cv = (statistics.stdev(filtered) / mean) if len(filtered) > 1 and mean != 0 else 0.0

    # Outliers usando Tukey
    q1 = statistics.quantiles(filtered, n=4)[0]
    q3 = statistics.quantiles(filtered, n=4)[2]
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = [x for x in filtered if x < lower or x > upper]

    # Porcentaje de outliers
    outlier_percent = (len(outliers) / len(filtered)) * 100

    return mean, cv, outlier_percent



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
    if not vpn_pkts:
        print("No OpenVPN traffic detected on that port.")
        sys.exit(1)

    # 2) Extract TLS handshake records
    tls_pkts = extract_tls(pcap, port,False)

    # 3) Segment into connections (start at CLIENT_V2, end at first P_DATA_V2)
    conns = []
    curr = None
    for msg, t, sz in vpn_pkts:
        if msg == 'P_CONTROL_HARD_RESET_CLIENT_V2':
            if curr:
                conns.append(curr)
            curr = {'start': t, 'sizes': [sz], 'end': None}
        elif curr:
            curr['sizes'].append(sz)
            if msg == 'P_DATA_V2' and curr['end'] is None:
                curr['end'] = t
                conns.append(curr)
                curr = None

    if not conns:
        print("No full VPN connections (control→data) found.")
        sys.exit(1)

    handshake_times = []
    vpn_times = []

    print(f"\nFound {len(conns)} VPN handshakes:\n")
    

    # 4) For each connection, compute metrics and print without CV
    for idx, c in enumerate(conns, start=1):
        t0 = c['start']
        

        # 1. Buscar tiempo del P_CONTROL_HARD_RESET_SERVER_V2 (inicio servidor)
        t_reset_server = next((t for (msg, t, sz) in vpn_pkts if msg == 'P_CONTROL_HARD_RESET_SERVER_V2' and t > t0), None)
        if not t_reset_server:
            print(f"Connection {idx}: no P_CONTROL_HARD_RESET_SERVER_V2 found, skipping.")
            continue

        # 2. Buscar primer P_CONTROL_V1 después del reset del servidor
        t_v1 = next((t for (msg, t, sz) in vpn_pkts if msg == 'P_CONTROL_V1' and t > t_reset_server), None)

        # 3. Buscar ClientHello (por si no hay P_CONTROL_V1)
        ch = next(((t, sz) for (h, t, sz) in tls_pkts if h == 'Handshake' and t > t0), None)
        if not ch:
            print(f"Connection {idx}: incomplete TLS handshake, skipping.")
            continue

        t_ch, sz_ch = ch

        # 4. Determinar inicio real del handshake TLS
        tch = t_v1 if t_v1 else t_ch

        

        # buscar primer paquete ApplicationData después de 
        tfin = next((t for (h,t,sz) in tls_pkts if h in ('ApplicationData', 'ChangeCipherSpec') and t > tch), None)
        if not tfin:
            print(f"Connection {idx}: could not find final TLS record after ServerHello.")
            continue
        dt_hs = tfin - tch
        handshake_times.append(dt_hs)

        tls_count = sum(1 for (h, t, sz) in tls_pkts if tch <= t <= tfin)


        key = (sig_alg, kem_alg)
        expected = tls_packet_count_reference.get(key)

        if tch < t_ch:
            print(f"ℹ️  Used P_CONTROL_V1 before ClientHello as handshake start for {sig_alg}-{kem_alg}")

        if expected is not None:
            if tls_count != expected:
                print(f"❌ ALERT: TLS packet count mismatch for {sig_alg}-{kem_alg}")
                print(f"    Observed: {tls_count}, Expected: {expected}")
                sys.exit(1)
            else:
                print(f"✅ TLS packet count OK for {sig_alg}-{kem_alg} ({tls_count})")
        else:
            print(f"⚠️ No reference TLS count for {sig_alg}-{kem_alg}")

        dt_vpn = c['end'] - c['start']
        vpn_times.append(dt_vpn)


        vpn_count = len(c['sizes'])

        # Verificación con la tabla de referencia
        expected_vpn = vpn_packet_count_reference.get(key)

        if expected_vpn is not None:
            if vpn_count != expected_vpn:
                print(f"❌ ALERT: VPN packet count mismatch for {sig_alg}-{kem_alg}")
                print(f"    Observed: {vpn_count}, Expected: {expected_vpn}")
                #sys.exit(1)
            else:
                print(f"✅ VPN packet count OK for {sig_alg}-{kem_alg} ({vpn_count})")
        else:
            print(f"⚠️ No reference VPN count for {sig_alg}-{kem_alg}")

        print(f"Connection {idx}:")
        print(f"  Handshake Duration : {dt_hs*1000:7.3f} ms")
        print(f"  VPN Setup Time     : {dt_vpn*1000:7.3f} ms")

        # 5) Print overall averages with CV in English
        m_hs, cv_hs, out_hs = stats(handshake_times)
        m_vp, cv_vp, out_vp = stats(vpn_times)

        print("\n**********************************************")

        if m_hs > 0:
            print(f"Average handshake time: {m_hs*1000:.2f} ms (CV={cv_hs:.2f}) (O={out_hs:.2f}%)")
        else:
            print("Average handshake time: Not enough data")

        if m_vp > 0:
            print(f"Average VPN setup time: {m_vp*1000:.2f} ms (CV={cv_vp:.2f}) (O={out_vp:.2f}%)")
        else:
            print("Average VPN setup time: Not enough data")

        print("**********************************************\n")


if __name__ == '__main__':
    main()


