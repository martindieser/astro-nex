# Configuración para Desarrollo 

Este documento describe cómo preparar el entorno para desarrollar y probar cambios en **Astro-Nex** utilizando Docker y el script de automatización.

## 1. Requisitos Previos

*   **Docker Desktop** (con WSL2).
*   **VcXsrv** (X Server para Windows).
*   **Git Bash** (o cualquier terminal que soporte scripts `.sh` en Windows).


## 2. Configuración del Servidor Gráfico (VcXsrv)

Para ver la interfaz gráfica, **VcXsrv** debe estar corriendo con estos ajustes:

1.  Ejecuta **XLaunch**.
2.  `Multiple windows` -> `Display number: 0` -> `Next`.
3.  `Start no client` -> `Next`.
4.  **IMPORTANTE:** Marcar **Disable access control**.
5.  Click en *Finish*.


## 3. Uso del Script de Desarrollo

Para estandarizar el proceso, usamos el script `dev.sh`. Este script construye la imagen, configura el volumen y te entrega una consola lista para trabajar.

### Ejecución
Abre tu terminal y ejecuta el script pasando tu **IP local** como argumento:

```bash
./dev.sh 192.168.0.2
```

> **Nota:** Si no conoces tu IP, abre una terminal en Windows y escribe `ipconfig`. Busca "Dirección IPv4" en tu adaptador de red principal.


## 4. Flujo de Trabajo (Edit → Test → Repeat)

Una vez ejecutado el script, estarás dentro de la terminal de Linux del contenedor (`astronex@...:/app$`).

### El Ciclo de Pruebas
1.  **Edita el código:** Abre los archivos en Windows con tu editor favorito.
2.  **Guarda:** Los cambios se reflejan instantáneamente en el contenedor gracias al volumen.
3.  **Ejecuta en la terminal de Docker:**
    ```bash
    python nex.py
    ```
4.  **Cerrar shell:** Usar comando `exit`


## 5. Parámetros Técnicos del Entorno

*   **Imagen:** `astronex-legacy` (Ubuntu 18.04 + Python 2.7).
*   **Volumen:** Se monta la carpeta raíz del proyecto en `/app`.
*   **Display:** Se redirige al servidor X de Windows mediante la IP pasada por argumento en el puerto `:0`.
