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

def render_oled_frame(bpm, spo2, samples, temperature=None, humidity=None):
    """Render the exact 128×64 monochrome frame used by the physical OLED."""
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("1", (128, 64)); draw = ImageDraw.Draw(image)
    small = ImageFont.load_default(size=8)
    draw.text((1, 2), "BPM", fill=255, font=small)
    draw_bitmap_value(draw, 21, 0, str(int(bpm)) if bpm is not None else "--", 2)
    draw.text((57, 2), "SpO2", fill=255, font=small)
    spo2_end = draw_bitmap_value(draw, 85, 0, str(int(spo2)) if spo2 is not None else "--", 2)
    draw.text((spo2_end + 1, 2), "%", fill=255, font=small)
    draw.text((2, 16), "T", fill=255, font=small)
    temp_value = f"{temperature:.1f}" if temperature is not None else "--.-"
    temp_end = draw_bitmap_value(draw, 10, 17, temp_value, 1)
    draw.text((temp_end, 16), "C", fill=255, font=small)
    draw.text((68, 16), "H", fill=255, font=small)
    humidity_end = draw_bitmap_value(draw, 77, 17, str(round(humidity)) if humidity is not None else "--", 1)
    draw.text((humidity_end + 1, 16), "%", fill=255, font=small)
    draw.line((0, 28, 127, 28), fill=255)
    values = samples[-64:]
    if len(values) > 1:
        low, high = min(values), max(values); span = max(high-low, 1)
        points = [(int(i*127/(len(values)-1)), int(62-(v-low)*30/span)) for i,v in enumerate(values)]
        draw.line(points, fill=255, width=1)
    else:
        draw.text((19, 42), "Esperando PPG", fill=255, font=small)
    return image

def draw_bitmap_value(draw, x, y, value, scale):
    """Draw numeric readings with a compact, crisp 5×7 pixel font."""
    glyphs = {
        "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
        "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
        "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
        "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
        "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
        "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
        "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
        "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
        "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
        "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
        "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    }
    cursor = x
    for char in value:
        if char in glyphs:
            for row, pattern in enumerate(glyphs[char]):
                for column, pixel in enumerate(pattern):
                    if pixel == "1":
                        left, top = cursor + column * scale, y + row * scale
                        draw.rectangle((left, top, left + scale - 1, top + scale - 1), fill=255)
            cursor += 5 * scale + scale
        elif char == ".":
            draw.rectangle((cursor, y + 6 * scale, cursor + scale - 1, y + 7 * scale - 1), fill=255)
            cursor += 2 * scale
    return cursor

def draw_oled(device, bpm, spo2, samples, temperature=None, humidity=None):
    if device is not None:
        device.display(render_oled_frame(bpm, spo2, samples, temperature, humidity))
