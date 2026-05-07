FROM ubuntu:18.04

# Evitar prompts interactivos durante la instalación
ENV DEBIAN_FRONTEND=noninteractive

# Actualizar e instalar dependencias de Astro-Nex y X11
RUN apt-get update && apt-get install -y \
    python2.7 \
    python2.7-dev \
    build-essential \
    swig \
    python-gtk2 \
    python-cairo \
    python-tz \
    python-configobj \
    python-pil \
    python-ipython \
    libcanberra-gtk-module \
    libcanberra-gtk3-module \
    fonts-dejavu \
    ttf-bitstream-vera \
    x11-apps \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Crear un usuario para evitar correr como root y mejorar compatibilidad con X11
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} astronex && \
    useradd -l -u ${USER_ID} -g astronex -m astronex && \
    echo "astronex ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER astronex
WORKDIR /app

# Variable de entorno para que Python encuentre los módulos locales
# Priorizamos la carpeta donde estarán los binarios de Linux compilados
ENV PYTHONPATH="/usr/local/lib/pysw:/app"

# Compilar la extensión C (SWIG)
USER root
COPY ext/ /app/ext/
RUN mkdir -p /usr/local/lib/pysw && \
    cd /app/ext/ext64 && \
    swig -python pysw.i && \
    gcc -O2 -fPIC -c pysw_wrap.c -I/usr/include/python2.7 -I/usr/lib/python2.7/config && \
    gcc -shared pysw_wrap.o -o _pysw.so -L. -lswe -lm && \
    cp pysw.py /usr/local/lib/pysw/pysw.py && \
    cp _pysw.so /usr/local/lib/pysw/_pysw.so

# Copiar el código fuente de la aplicación
COPY astronex/ /app/astronex/
COPY nex.py /app/

# Instalar la fuente necesaria
USER root
COPY astronex/resources/Astro-Nex.ttf /usr/share/fonts/truetype/
RUN fc-cache -f -v
USER astronex

# Comando por defecto para ejecutar la aplicación
# Se asume que el directorio del proyecto se montará en /app
ENTRYPOINT ["python2.7", "nex.py"]
