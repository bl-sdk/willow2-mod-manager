FROM alpine:latest AS clang-cross
CMD ["/bin/bash"]
RUN <<EOF
    apk add --no-cache      \
        bash                \
        clang               \
        clang-extra-tools   \
        cmake               \
        git                 \
        lld                 \
        llvm                \
        msitools            \
        ninja               \
        openssh             \
        perl                \
        python3             \
        py3-requests
    git clone https://github.com/mstorsjo/msvc-wine.git
    msvc-wine/vsdownload.py \
        --accept-license \
        --dest /win-sdk \
        Microsoft.VisualStudio.Workload.VCTools \
        --arch x86 x64
    msvc-wine/install.sh /win-sdk
    rm -r msvc-wine
EOF

# llvm-mingw comes with pre-built ubuntu binaries, so using that
FROM ubuntu:latest AS llvm-mingw
CMD ["/bin/bash"]
RUN <<EOF
    apt-get update
    DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC \
        apt-get install -y      \
            cmake               \
            git                 \
            msitools            \
            ninja-build         \
            python-is-python3   \
            python3             \
            python3-requests    \
            wget                \
            xz-utils
    wget -nv https://github.com/mstorsjo/llvm-mingw/releases/download/20250114/llvm-mingw-20250114-msvcrt-ubuntu-20.04-x86_64.tar.xz
    tar -xf llvm-mingw-20250114-msvcrt-ubuntu-20.04-x86_64.tar.xz
    rm llvm-mingw-20250114-msvcrt-ubuntu-20.04-x86_64.tar.xz
    mv llvm-mingw-20250114-msvcrt-ubuntu-20.04-x86_64 /llvm-mingw
EOF
ENV PATH="/llvm-mingw/bin:$PATH"

FROM alpine:latest AS mingw
CMD ["/bin/bash"]
RUN <<EOF
    apk add --no-cache      \
        bash                \
        cmake               \
        git                 \
        i686-mingw-w64-gcc  \
        mingw-w64-gcc       \
        msitools            \
        ninja               \
        openssh             \
        py3-requests        \
        python3
EOF
