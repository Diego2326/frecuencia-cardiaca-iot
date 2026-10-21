"""Shared HTTP sender and OLED rendering for the Orange Pi and simulator."""
import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

SERVER_URL = os.getenv("SERVER_URL", "https://localhost:8080").rstrip("/")
DEVICE_TOKEN = os.getenv("DEVICE_TOKEN", "")
SEND_INTERVAL = float(os.getenv("SEND_INTERVAL", "1"))

class Sender:
    def __init__(self):
        if not DEVICE_TOKEN:
            raise RuntimeError("Set DEVICE_TOKEN in the device environment")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {DEVICE_TOKEN}", "Content-Type": "application/json"})

    def send(self, packet):
        delay = 1.0
        while True:
            try:
                response = self.session.post(f"{SERVER_URL}/api/telemetry/ingest", json=packet, timeout=8)
                response.raise_for_status()
                return
            except requests.RequestException as exc:
                print(f"Send failed ({exc}); retrying in {delay:.0f}s", flush=True)
                time.sleep(delay)
                delay = min(delay * 2, 30)

def make_oled():
    """Select SSD1306 or SH1106 explicitly; auto mode probes the common I2C addresses."""
    try:
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306, sh1106
        kind = os.getenv("OLED_DRIVER", "auto").lower()
        address = int(os.getenv("I2C_ADDRESS", "0x3c"), 0)
        serial = i2c(port=int(os.getenv("I2C_BUS", "0")), address=address)
        if kind == "ssd1306": return ssd1306(serial, width=128, height=64)
        if kind == "sh1106": return sh1106(serial, width=128, height=64)
        # Controller cannot be identified reliably over I2C. Use the common SSD1306 default;
        # setting OLED_DRIVER=sh1106 selects the other compatible controller.
        return ssd1306(serial, width=128, height=64)
    except Exception as exc:
        print(f"OLED unavailable: {exc}", flush=True)
        return None

def render_oled_frame(bpm, spo2, samples):
    """Render the exact 128×64 monochrome frame used by the physical OLED."""
    from PIL import Image, ImageDraw
    image = Image.new("1", (128, 64)); draw = ImageDraw.Draw(image)
    draw.text((2, 1), f"BPM {int(bpm) if bpm is not None else '--'}", fill=255)
    draw.text((69, 1), f"SpO2 {int(spo2) if spo2 is not None else '--'}", fill=255)
    draw.line((0, 15, 127, 15), fill=255)
    values = samples[-64:]
    if len(values) > 1:
        low, high = min(values), max(values); span = max(high-low, 1)
        points = [(int(i*127/(len(values)-1)), int(57-(v-low)*37/span)) for i,v in enumerate(values)]
        draw.line(points, fill=255, width=1)
    else:
        draw.text((19, 35), "Esperando PPG", fill=255)
    return image

def draw_oled(device, bpm, spo2, samples):
    if device is not None:
        device.display(render_oled_frame(bpm, spo2, samples))
