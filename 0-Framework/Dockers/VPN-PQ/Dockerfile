# Define build arguments for version tags, installation paths, and configurations
ARG UBUNTU_VERSION=24.10
ARG OPENSSL_TAG=openssl-3.4
ARG LIBOQS_TAG=0.12.0
ARG OQSPROVIDER_TAG=0.8.0
ARG OPENVPN_TAG=v2.6.12
ARG INSTALLDIR=/opt/oqssa
ARG OPENVPNDIR=/home/openvpn
ARG BASEDIR=/opt
ARG LIBOQSDIR=${BASEDIR}/liboqs


# Specify supported key encapsulation mechanisms (KEM) algorithms
ARG KEM_ALGLIST="mlkem768:p384_mlkem768"

# Stage 1: Build - Compile and assemble all necessary components and dependencies
FROM ubuntu:${UBUNTU_VERSION} AS intermediate

# 1) Escribe sources.list apuntando a old-releases
RUN set -eux; \
  mv /etc/apt/sources.list /etc/apt/sources.list.bak || true; \
  cat > /etc/apt/sources.list <<'EOF'
deb http://old-releases.ubuntu.com/ubuntu oracular main restricted universe multiverse
deb http://old-releases.ubuntu.com/ubuntu oracular-updates main restricted universe multiverse
deb http://old-releases.ubuntu.com/ubuntu oracular-backports main restricted universe multiverse
deb http://old-releases.ubuntu.com/ubuntu oracular-security main restricted universe multiverse
EOF

# 2) Sustituye cualquier entrada residual (.list y .sources), desactiva Valid-Until e instala
RUN set -eux; \
  find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -print -exec sed -i \
    -e 's|https\?://archive\.ubuntu\.com/ubuntu|http://old-releases.ubuntu.com/ubuntu|g' \
    -e 's|https\?://security\.ubuntu\.com/ubuntu|http://old-releases.ubuntu.com/ubuntu|g' \
    -e 's|https\?://ports\.ubuntu\.com/ubuntu-ports|http://old-releases.ubuntu.com/ubuntu|g' {} \; || true; \
  printf 'Acquire::Check-Valid-Until "false";\n' > /etc/apt/apt.conf.d/99no-check-valid; \
  apt-get update; \
  apt-get install -y --no-install-recommends \
    cmake gcc ninja-build libunwind-dev \
    pkg-config build-essential \
    cargo git wget ca-certificates \
    openssl libssl-dev; \
  rm -rf /var/lib/apt/lists/*


LABEL version="3"

ARG OPENSSL_TAG
ARG LIBOQS_TAG
ARG OQSPROVIDER_TAG
ARG OPENVPN_TAG
ARG INSTALLDIR
ARG KEM_ALGLIST
ARG OPENVPNDIR
ARG LIBOQSDIR

ENV DEBIAN_FRONTEND=noninteractive
ENV OPENSSL3_DIR=${INSTALLDIR}

# Install required build tools and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
            libtool automake autoconf cmake ninja-build ca-certificates \
            make openssl libssl-dev pkg-config libcap-ng-dev \
            git net-tools liblzo2-dev \
             libpam0g-dev python3-docutils \
            libnl-3-dev libnl-genl-3-dev  \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Download and prepare source files needed for the build process
WORKDIR /opt
RUN git clone --depth 1 --branch ${LIBOQS_TAG} https://github.com/open-quantum-safe/liboqs && \
    git clone --depth 1 --branch ${OPENSSL_TAG} https://github.com/montenegro-montes/openssl.git && \
    git clone --depth 1 --branch ${OQSPROVIDER_TAG} https://github.com/open-quantum-safe/oqs-provider.git && \
    git clone --depth 1 --branch ${OPENVPN_TAG} https://github.com/OpenVPN/openvpn.git

# Build and install liboqs
WORKDIR /opt/liboqs/build
RUN cmake -G"Ninja" ..  \
    -DCMAKE_INSTALL_PREFIX=${INSTALLDIR} && ninja install

# Build and install OpenSSL
WORKDIR /opt/openssl
RUN openssl_libdir='lib64' && if [ "$(uname -m)" = "aarch64" ]; then openssl_libdir='lib'; fi && \
    LDFLAGS="-Wl,-rpath -Wl,${INSTALLDIR}/$openssl_libdir" ./config shared --prefix=${INSTALLDIR} && \
    make -j"$(nproc)" && make install_sw install_ssldirs;

# Set PATH to include the new OpenSSL binaries
ENV PATH="${INSTALLDIR}/bin:${PATH}"

# Build, install, and configure the oqs-provider for OpenSSL integration
WORKDIR /opt/oqs-provider
RUN ln -s ../openssl . && \
    openssl_libdir='lib64' && if [ "$(uname -m)" = "aarch64" ]; then openssl_libdir='lib'; fi && \
    cmake -DOPENSSL_ROOT_DIR=${INSTALLDIR} -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=${INSTALLDIR} -S . -B _build && \
    cmake --build _build  && cp _build/lib/oqsprovider.so ${INSTALLDIR}/$openssl_libdir/ossl-modules && \
    sed -i "s/default = default_sect/default = default_sect\noqsprovider = oqsprovider_sect/g" /opt/oqssa/ssl/openssl.cnf && \
    sed -i "s/\[default_sect\]/\[default_sect\]\nactivate = 1\n\[oqsprovider_sect\]\nactivate = 1\n/g" /opt/oqssa/ssl/openssl.cnf && \
    sed -i "s/providers = provider_sect/providers = provider_sect\nssl_conf = ssl_sect\n\n\[ssl_sect\]\nsystem_default = system_default_sect\n\n\[system_default_sect\]\nGroups = ${KEM_ALGLIST}\n/g" /opt/oqssa/ssl/openssl.cnf

# Build and install OpenVPN with the new OpenSSL
WORKDIR /opt/openvpn
RUN openssl_libdir='lib64' && if [ "$(uname -m)" = "aarch64" ]; then openssl_libdir='lib'; fi && \
    libtoolize --force && aclocal && autoheader && \
    automake --force-missing --add-missing && autoconf && \
    CFLAGS="-I$OPENSSL3_DIR/include -Wl,-rpath=$OPENSSL3_DIR/$openssl_libdir -L$OPENSSL3_DIR/$openssl_libdir" ./configure --prefix=${INSTALLDIR} --disable-lz4 && \
    make -j"$(nproc)" && make check && make install

# ---------- Build ldkeylog.so for key logging ----------
# This will compile and install the key logging library
WORKDIR /opt/ldkeylog
RUN apt-get update && apt-get install -y build-essential curl && \
    curl -L -o ldkeylog.c https://gist.githubusercontent.com/hlandau/f67b4065909913ed31da1500dc4a8719/raw/ldkeylog.c && \
    cc -shared -fPIC -O3 -o ldkeylog.so ldkeylog.c -ldl -pthread

RUN cp ${LIBOQSDIR}/build/tests/vectors_kem ${INSTALLDIR}/bin/

# Stage 2: Runtime - Create a lightweight image with essential binaries and configurations
FROM ubuntu:${UBUNTU_VERSION}

ARG INSTALLDIR
ARG OPENVPNDIR


# 1) Escribe sources.list apuntando a old-releases
RUN set -eux; \
  mv /etc/apt/sources.list /etc/apt/sources.list.bak || true; \
  cat > /etc/apt/sources.list <<'EOF'
deb http://old-releases.ubuntu.com/ubuntu oracular main restricted universe multiverse
deb http://old-releases.ubuntu.com/ubuntu oracular-updates main restricted universe multiverse
deb http://old-releases.ubuntu.com/ubuntu oracular-backports main restricted universe multiverse
deb http://old-releases.ubuntu.com/ubuntu oracular-security main restricted universe multiverse
EOF

# 2) Sustituye cualquier entrada residual (.list y .sources), desactiva Valid-Until e instala
RUN set -eux; \
  find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -print -exec sed -i \
    -e 's|https\?://archive\.ubuntu\.com/ubuntu|http://old-releases.ubuntu.com/ubuntu|g' \
    -e 's|https\?://security\.ubuntu\.com/ubuntu|http://old-releases.ubuntu.com/ubuntu|g' \
    -e 's|https\?://ports\.ubuntu\.com/ubuntu-ports|http://old-releases.ubuntu.com/ubuntu|g' {} \; || true; \
  printf 'Acquire::Check-Valid-Until "false";\n' > /etc/apt/apt.conf.d/99no-check-valid; \
  apt-get update; \
  apt-get install -y --no-install-recommends \
    ca-certificates iproute2 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install essential runtime tools and libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    liblzo2-2 libnl-3-200 libnl-genl-3-200 \
    procps net-tools iputils-ping ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p ${OPENVPNDIR}

# Copy only the required contents from the intermediate stage
COPY --from=intermediate ${INSTALLDIR} ${INSTALLDIR}


# Stage 2: Runtime (continued)

# Add this line in the final image stage to copy the compiled .so
COPY --from=intermediate /opt/ldkeylog/ldkeylog.so /ldkeylog.so

# Optional: predefine SSLKEYLOGFILE path (can be overwritten at runtime)
#ENV SSLKEYLOGFILE=/sslkeys/sslkeys.log

# Export key logging via LD_PRELOAD
#ENV LD_PRELOAD=/ldkeylog.so

# Set PATH to include OpenSSL and OpenVPN binaries
ENV PATH="${INSTALLDIR}/bin:${INSTALLDIR}/sbin:${PATH}"

# Copy configuration files and scripts
COPY scripts/*.sh ${INSTALLDIR}/bin


COPY cfg/openvpn-openssl.cnf ${OPENVPNDIR}
COPY cfg/*.config ${OPENVPNDIR}



# Set working directory for the OpenVPN service
WORKDIR ${OPENVPNDIR}

STOPSIGNAL SIGTERM