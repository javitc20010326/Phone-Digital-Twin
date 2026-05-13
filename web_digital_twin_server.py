import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from redmi_desktop_twin import HTTP_PORT, UDP_PORT, SensorBridge


APP_DIR = Path(__file__).resolve().parent
VIEWER_HTML = APP_DIR / "web_digital_twin.html"
APK_FILE = APP_DIR / "android-sensor-sender" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"


class WebTwinState:
    def __init__(self):
        self.bridge = SensorBridge()
        self.received = 0
        self.last_type = ""
        self.active = True

    def update(self, payload, source):
        if not self.active:
            return
        self.received += 1
        self.last_type = str(payload.get("type") or payload.get("sensor") or "")
        self.bridge.update_from_payload(payload, source)

    def toggle(self):
        self.active = not self.active
        return self.active

    def set_active(self, active):
        self.active = bool(active)
        return self.active

    def snapshot(self):
        matrix, raw, source, last_at = self.bridge.snapshot()
        motion, motion_at = self.bridge.motion_snapshot()
        now = time.time()
        return {
            "ok": True,
            "active": self.active,
            "received": self.received,
            "lastType": self.last_type,
            "source": source,
            "age": None if last_at <= 0 else now - last_at,
            "motionAge": None if motion_at <= 0 else now - motion_at,
            "matrix": matrix,
            "raw": raw,
            "motion": motion,
            "serverTime": now,
        }


STATE = WebTwinState()


class WebTwinHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        route = urlparse(self.path).path
        if route in ("/", "/viewer", "/viewer.html"):
            self._send_file(VIEWER_HTML, "text/html; charset=utf-8")
            return

        if route in ("/state", "/status"):
            self._send_json(STATE.snapshot())
            return

        if route == "/health":
            self._send_json({"ok": True, "port": HTTP_PORT, "udpPort": UDP_PORT, "active": STATE.active})
            return

        if route == "/download":
            self._send_download_page()
            return

        if route == "/control":
            self._send_json({"ok": True, "active": STATE.active})
            return

        if route in ("/apk", "/apk/phone-digital-twin.apk"):
            self._send_file(
                APK_FILE,
                "application/vnd.android.package-archive",
                attachment_name="phone-digital-twin.apk",
            )
            return

        self.send_error(404)

    def do_HEAD(self):
        route = urlparse(self.path).path
        if route in ("/apk", "/apk/phone-digital-twin.apk"):
            try:
                size = APK_FILE.stat().st_size
            except OSError:
                self.send_error(404)
                return
            self.send_response(200)
            self._common_headers()
            self.send_header("Content-Type", "application/vnd.android.package-archive")
            self.send_header("Content-Disposition", 'attachment; filename="phone-digital-twin.apk"')
            self.send_header("Content-Length", str(size))
            self.end_headers()
            return
        if route == "/health":
            body = json.dumps({"ok": True, "port": HTTP_PORT, "udpPort": UDP_PORT, "active": STATE.active}).encode("utf-8")
            self.send_response(200)
            self._common_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return
        self.send_error(404)

    def do_POST(self):
        route = urlparse(self.path).path
        if route == "/control":
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length) if length > 0 else b"{}"
            try:
                payload = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                payload = {}
            action = str(payload.get("action") or "toggle").lower()
            if action == "on":
                active = STATE.set_active(True)
            elif action == "off":
                active = STATE.set_active(False)
            else:
                active = STATE.toggle()
            self._send_json({"ok": True, "active": active})
            return

        if route != "/sensor":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        if not isinstance(payload, dict):
            self.send_error(400, "Expected JSON object")
            return

        client_ip = self.client_address[0] if self.client_address else "unknown"
        STATE.update(payload, f"APK / HTTP {client_ip}")
        self.send_response(204)
        self._common_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self._common_headers()
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send_file(self, path, content_type, attachment_name=None):
        try:
            body = path.read_bytes()
        except OSError:
            self.send_error(404)
            return
        self.send_response(200)
        self._common_headers()
        self.send_header("Content-Type", content_type)
        if attachment_name:
            self.send_header("Content-Disposition", f'attachment; filename="{attachment_name}"')
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_download_page(self):
        body = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Phone Digital Twin APK</title>
  <style>
    body {{ margin: 0; font-family: system-ui, Segoe UI, sans-serif; background: #0b0f14; color: #e8eef5; }}
    main {{ max-width: 680px; margin: 0 auto; padding: 34px 22px; }}
    h1 {{ font-size: 28px; margin: 0 0 14px; }}
    p {{ color: #aeb9c4; line-height: 1.45; }}
    a.button {{ display: block; text-align: center; margin: 22px 0; padding: 16px 18px; border-radius: 8px; background: #2ee67a; color: #031009; font-weight: 800; text-decoration: none; }}
    code {{ display: block; padding: 12px; border: 1px solid #273442; border-radius: 8px; color: #75d7ff; background: #101820; overflow-wrap: anywhere; }}
  </style>
</head>
<body>
  <main>
    <h1>Phone Digital Twin</h1>
    <p>Descarga la APK actualizada para enviar sensores por UDP al gemelo digital del PC.</p>
    <a class="button" href="/apk/phone-digital-twin.apk">Descargar APK</a>
    <p>Endpoint recomendado en la APK:</p>
    <code>udp://192.168.1.193:5005</code>
    <p>Si Android avisa de instalacion desconocida, permite instalar desde este navegador.</p>
  </main>
</body>
</html>""".encode("utf-8")
        self.send_response(200)
        self._common_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(200)
        self._common_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _common_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Content-Type-Options", "nosniff")

    def log_message(self, fmt, *args):
        return


def local_ip_links():
    links = [f"http://localhost:{HTTP_PORT}/"]
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.settimeout(0.2)
        probe.connect(("8.8.8.8", 80))
        ip = probe.getsockname()[0]
        probe.close()
        if ip and not ip.startswith("127."):
            links.append(f"http://{ip}:{HTTP_PORT}/")
    except OSError:
        pass
    return links


def run_udp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    while True:
        data, addr = sock.recvfrom(8192)
        try:
            payload = json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            STATE.update(payload, f"APK / UDP {addr[0]}:{addr[1]}")


def main():
    udp_thread = threading.Thread(target=run_udp_server, daemon=True)
    udp_thread.start()
    server = ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), WebTwinHandler)
    print("Phone Digital Twin webserver activo.")
    for link in local_ip_links():
        print(f"Viewer: {link}")
    print(f"Sensor endpoint APK USB/ADB reverse: http://127.0.0.1:{HTTP_PORT}/sensor")
    print(f"Sensor endpoint UDP LAN: udp://IP_DEL_PC:{UDP_PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
