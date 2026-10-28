# syntax=docker/dockerfile:1
# Default: public board-free learning environment.
# Hardware: override with the documented public Quartus 26.1.1 image digest.
ARG BASE_IMAGE=ubuntu:24.04
FROM ${BASE_IMAGE}
USER root
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build git curl ca-certificates xz-utils gcc-aarch64-linux-gnu \
    python3 python3-venv device-tree-compiler libssl-dev zlib1g-dev \
    qemu-system-arm gdb-multiarch verilator libusb-1.0-0 libudev1 usbutils \
    iproute2 procps util-linux \
    && rm -rf /var/lib/apt/lists/*
COPY install-arm.sh /tmp/install-arm.sh
RUN bash /tmp/install-arm.sh && rm /tmp/install-arm.sh
ARG USER_UID=1000
ARG USER_GID=1000
RUN if getent passwd "$USER_UID" >/dev/null; then \
      old_user=$(getent passwd "$USER_UID" | cut -d: -f1); \
      usermod -l dev -d /home/dev -m -s /bin/bash "$old_user"; \
    else useradd -m -u "$USER_UID" -s /bin/bash dev; fi \
    && if ! getent group "$USER_GID" >/dev/null; then groupadd -g "$USER_GID" lab; fi \
    && usermod -g "$USER_GID" dev
ENV ARM_BAREMETAL_ROOT=/opt/arm-gnu-toolchain-13.2.Rel1-x86_64-aarch64-none-elf \
    CROSS_COMPILE=aarch64-none-elf- \
    QUARTUS_ROOTDIR=/opt/altera/quartus \
    PATH=/opt/arm-gnu-toolchain-13.2.Rel1-x86_64-aarch64-none-elf/bin:/opt/altera/quartus/bin:/opt/altera/qsys/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
USER dev
WORKDIR /home/dev
ENTRYPOINT []
CMD ["sleep", "infinity"]
