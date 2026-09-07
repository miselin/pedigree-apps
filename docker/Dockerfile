ARG PEDIGREE_BUILDER_IMAGE=ghcr.io/miselin/pedigree-builder@sha256:14bf372f9d20b6bedda051265e8b6b0bcd98cf429626b55f7d05ce55c2252f75
FROM ${PEDIGREE_BUILDER_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        autoconf \
        automake \
        binutils \
        bzip2 \
        ccache \
        curl \
        file \
        gperf \
        help2man \
        libglib2.0-dev-bin \
        libtool \
        make \
        ninja-build \
        patch \
        patchelf \
        perl \
        pkg-config \
        python3-pip \
        python3-venv \
        tar \
        texinfo \
        unzip \
        xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/pedigree-apps \
    && /opt/pedigree-apps/bin/pip install --no-cache-dir --upgrade pip

COPY requirements.txt /tmp/pedigree-apps/requirements.txt
COPY pup /tmp/pedigree-apps/pup
RUN /opt/pedigree-apps/bin/pip install --no-cache-dir \
        -r /tmp/pedigree-apps/requirements.txt \
        /tmp/pedigree-apps/pup \
    && rm -rf /tmp/pedigree-apps

ENV PATH="/opt/pedigree-apps/bin:/opt/pedigree/bin:${PATH}" \
    PEDIGREE_APPS_CONTAINER=1 \
    PEDIGREE_APPS_ROOT=/workspace \
    PEDIGREE_SOURCE_ROOT=/pedigree \
    PEDIGREE_TOOLCHAIN_ROOT=/opt/pedigree

WORKDIR /workspace

LABEL org.opencontainers.image.source="https://github.com/miselin/pedigree-apps" \
      org.opencontainers.image.description="Local FHS ports builder for Pedigree"

CMD ["python3", "buildPackages.py", "--help"]
