"""Serve an exact OLED framebuffer preview of the current Cloud Run telemetry."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
import webbrowser

import requests

from common import DEVICE_TOKEN, SERVER_URL, render_oled_frame

HOST = "127.0.0.1"
PORT = 8765
ROOT = Path(__file__).parent


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        route = self.path.split("?", 1)[0]
        if route in ("/", "/oled_preview.html"):
            payload = (ROOT / "oled_preview.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if route != "/frame.png":
            self.send_error(404)
            return
        try:
            response = requests.get(
                f"{SERVER_URL}/api/telemetry/latest",
                headers={"Authorization": f"Bearer {DEVICE_TOKEN}"},
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()
            frame = render_oled_frame(data.get("bpm"), data.get("spo2"), data.get("ppg", []),
                                      data.get("temperature"), data.get("humidity"))
            image = BytesIO()
            frame.save(image, format="PNG")
            payload = image.getvalue()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (requests.RequestException, ValueError, OSError) as exc:
            payload = f"Could not read Cloud Run telemetry: {exc}".encode()
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    def log_message(self, _format, *_args):
        pass


def main():
    if not DEVICE_TOKEN:
        raise RuntimeError("Set DEVICE_TOKEN in device/.env before opening the OLED preview")
    server = ThreadingHTTPServer((HOST, PORT), PreviewHandler)
    url = f"http://{HOST}:{PORT}/oled_preview.html"
    print(f"OLED preview: {url}", flush=True)
    print(f"Using telemetry from {SERVER_URL}", flush=True)
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nOLED preview stopped", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
