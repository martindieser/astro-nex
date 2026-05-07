FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-dev \
    python3-pip \
    build-essential \
    swig \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    python3-cairo \
    python3-tz \
    python3-pil \
    libcanberra-gtk-module \
    libcanberra-gtk3-module \
    fonts-dejavu \
    ttf-bitstream-vera \
    x11-apps \
    sudo \
    && pip3 install configobj path \
    && rm -rf /var/lib/apt/lists/*

ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} astronex && \
    useradd -l -u ${USER_ID} -g astronex -m astronex && \
    echo "astronex ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER astronex
WORKDIR /app

ENV PYTHONPATH="/usr/local/lib/pysw:/app"

USER root
COPY ext/ /app/ext/
RUN mkdir -p /usr/local/lib/pysw && \
    cd /app/ext/ext64 && \
    swig -python -py3 pysw.i && \
    gcc -O2 -fPIC -c pysw_wrap.c -I/usr/include/python3 -I$(python3 -c "import sysconfig; print(sysconfig.get_path('include'))") && \
    gcc -shared pysw_wrap.o -o _pysw.so -L. -lswe -lm && \
    cp pysw.py /usr/local/lib/pysw/pysw.py && \
    cp _pysw.so /usr/local/lib/pysw/_pysw.so

COPY astronex/ /app/astronex/
COPY nex.py /app/

USER root
COPY astronex/resources/Astro-Nex.ttf /usr/share/fonts/truetype/
RUN fc-cache -f -v

USER astronex

ENTRYPOINT ["python3", "nex.py"]