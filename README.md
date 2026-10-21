# Pulse Monitor IoT

Monolito Node.js/TypeScript con Express, Socket.IO y React/Vite. La aplicación conserva en memoria la última lectura y como máximo `MAX_PPG_SAMPLES` muestras PPG. No usa base de datos. El modo de simulación y el de hardware publican el mismo formato autenticado.

## Requisitos

- Node.js 20 o 22 y npm
- Python 3.10 o superior para el simulador/Orange Pi
- Para hardware: Orange Pi Zero 2W con I²C habilitado, MAX30102, AHT10 y OLED I²C 128×64

## Desarrollo local

```sh
cp .env.example .env
# Edite DEVICE_TOKEN y use el mismo valor en el dispositivo.
npm install
npm run dev
```

La web queda en `http://localhost:5173`; Express y Socket.IO escuchan en el puerto 8080. El archivo `device/.env.example` ya apunta al servicio Cloud Run desplegado. Copie ese archivo a `device/.env`, coloque el mismo token configurado en Cloud Run y ejecute el simulador. Para probar localmente con HTTP sin TLS, cambie `SERVER_URL=http://localhost:8080` en ese archivo (el token debe coincidir con `.env`):

```sh
cd device
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python simulate.py
```

La etiqueta amarilla **SIMULACIÓN** aparece cuando esos datos están activos. Para producción, `SERVER_URL` debe ser una URL HTTPS.

## Sensores en Orange Pi

Active I²C en Armbian, conecte SDA/SCL/GND y alimente módulos a 3.3 V. Compruebe la dirección con `i2cdetect -y <bus>` (habitualmente MAX30102 `0x57`, AHT10 `0x38`, OLED `0x3c`). Instale las dependencias Python y ejecute:

```sh
python sensors.py
```

Configure en `device/.env` `SERVER_URL`, `DEVICE_TOKEN`, `I2C_BUS`, y si hace falta las direcciones. Defina `OLED_DRIVER=ssd1306` o `OLED_DRIVER=sh1106`. El controlador no se puede identificar con fiabilidad mediante una lectura I²C genérica; `auto` selecciona SSD1306, que es el valor frecuente. Si la pantalla queda en blanco o desplazada, pruebe SH1106. El OLED muestra BPM, SpO₂ y la ventana de onda PPG.

El lector MAX30102 configura el FIFO en modo SpO₂ y extrae muestras IR (onda de pulso PPG). BPM y SpO₂ se estiman con detección de picos y una aproximación por razón de señales; la calidad depende del sensor, contacto y movimiento. No es un dispositivo médico. No se envían muestras ECG.

Para ejecutar las pruebas de los drivers sin conectar sensores:

```sh
cd device
.venv/bin/python -m unittest -v test_sensors.py
```

## Despliegue en Cloud Run

Cloud Run requiere un proyecto con facturación y APIs de Cloud Run y Artifact Registry habilitadas, `gcloud` autenticado y Docker disponible. El monolito sirve frontend, API y WebSockets por el puerto `PORT` que asigna Cloud Run. Para conservar el estado en memoria, limite el servicio a una instancia (los reinicios eliminan los datos):

```sh
gcloud config set project PROJECT_ID
gcloud run deploy pulse-monitor \
  --source . \
  --region REGION \
  --allow-unauthenticated \
  --max 1 \
  --min 0 \
  --timeout 3600 \
  --set-env-vars DEVICE_TOKEN='GENERATE_A_LONG_RANDOM_SECRET',MAX_PPG_SAMPLES=1200,STALE_AFTER_MS=15000
```

Restringir `--max 1` es importante porque Cloud Run escala horizontalmente y la memoria no se comparte entre instancias. El frontend se puede servir públicamente; el endpoint de envío requiere `Authorization: Bearer <DEVICE_TOKEN>`. En un servicio de producción, mantenga el token fuera del historial de shell y use Secret Manager si está disponible en el propio proyecto.

Los WebSockets de Cloud Run son conexiones HTTP sujetas al timeout configurado (máximo 60 minutos); el cliente Socket.IO reconecta automáticamente. Una conexión abierta cuenta como instancia activa y puede generar facturación mientras se atienden sockets. Cloud Run puede cerrar conexiones al desplegar o reiniciar una instancia. El modo mínimo cero puede añadir latencia al primer acceso.

## API y formato

`POST /api/telemetry/ingest` requiere el token y recibe JSON con `timestamp` ISO 8601, `bpm`, `spo2`, `temperature`, `humidity`, `ppg` (hasta 500 números por paquete) y `simulated` booleano. Los signos ausentes pueden ser `null`. `GET /api/telemetry/latest` devuelve la instantánea y el estado de frescura. `GET /api/health` es una comprobación básica de salud. El PPG se trunca a la ventana configurada para evitar crecimiento indefinido.
