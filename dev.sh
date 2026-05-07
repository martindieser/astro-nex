#!/bin/bash

DISPLAY=$1

# Construir la imagen
echo "Construyendo imagen Docker..."
docker build -t "astronex-legacy" .

echo "Usando DISPLAY=$DISPLAY"
echo "Iniciando Astro-Nex..."

# Ejecutar contenedor
docker run --rm -it \
    -e DISPLAY=$DISPLAY:0 \
    -v "$(pwd):/app" \
    --entrypoint /bin/bash \
    "astronex-legacy"
