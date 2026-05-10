import json
import math
import os
import queue
import socket
import threading
import time
import tkinter as tk
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


APP_DIR = Path(__file__).resolve().parent
PHONE_HTML = APP_DIR / "mobile_sensor_bridge.html"
HTTP_PORT = 8876
UDP_PORT = 5005


def identity():
    return ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def mat_mul(a, b):
    return tuple(
        tuple(sum(a[row][k] * b[k][col] for k in range(3)) for col in range(3))
        for row in range(3)
    )


def mat_vec(m, v):
    return (
        m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
        m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
        m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
    )


def transpose(m):
    return tuple(tuple(m[col][row] for col in range(3)) for row in range(3))


def rot_x(angle):
    c = math.cos(angle)
    s = math.sin(angle)
    return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))


def rot_y(angle):
    c = math.cos(angle)
    s = math.sin(angle)
    return ((c, 0.0, s), (0.0, 1.0, 0.0), (-s, 0.0, c))


def rot_z(angle):
    c = math.cos(angle)
    s = math.sin(angle)
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def from_euler(alpha_deg, beta_deg, gamma_deg):
    alpha = math.radians(alpha_deg or 0.0)
    beta = math.radians(beta_deg or 0.0)
    gamma = math.radians(gamma_deg or 0.0)
    return mat_mul(mat_mul(rot_z(alpha), rot_x(beta)), rot_y(gamma))


def quat_to_matrix(w, x, y, z):
    norm = math.sqrt(w * w + x * x + y * y + z * z) or 1.0
    w, x, y, z = w / norm, x / norm, y / norm, z / norm
    return (
        (1 - 2 * y * y - 2 * z * z, 2 * x * y - 2 * z * w, 2 * x * z + 2 * y * w),
        (2 * x * y + 2 * z * w, 1 - 2 * x * x - 2 * z * z, 2 * y * z - 2 * x * w),
        (2 * x * z - 2 * y * w, 2 * y * z + 2 * x * w, 1 - 2 * x * x - 2 * y * y),
    )


def rotation_vector_to_matrix(values):
    x, y, z = values[0], values[1], values[2]
    if len(values) >= 4:
        w = values[3]
    else:
        w = math.sqrt(max(0.0, 1.0 - x * x - y * y - z * z))
    return quat_to_matrix(w, x, y, z)


def lerp_matrix(a, b, amount):
    return orthonormalize(tuple(
        tuple(a[r][c] + (b[r][c] - a[r][c]) * amount for c in range(3))
        for r in range(3)
    ))


def orthonormalize(m):
    x = normalize((m[0][0], m[1][0], m[2][0]))
    y_raw = (m[0][1], m[1][1], m[2][1])
    dot_xy = dot(x, y_raw)
    y = normalize((y_raw[0] - dot_xy * x[0], y_raw[1] - dot_xy * x[1], y_raw[2] - dot_xy * x[2]))
    z = cross(x, y)
    return (
        (x[0], y[0], z[0]),
        (x[1], y[1], z[1]),
        (x[2], y[2], z[2]),
    )


def normalize(v):
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if length < 1e-9:
        return (1.0, 0.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def add_vec(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub_vec(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale_vec(v, amount):
    return (v[0] * amount, v[1] * amount, v[2] * amount)


def lerp_vec(a, b, amount):
    return (
        a[0] + (b[0] - a[0]) * amount,
        a[1] + (b[1] - a[1]) * amount,
        a[2] + (b[2] - a[2]) * amount,
    )


def vec_len(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def clamp(value, low, high):
    return max(low, min(high, value))


def get_lan_addresses():
    addresses = []
    hostname = socket.gethostname()
    try:
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in addresses:
                addresses.append(ip)
    except OSError:
        pass
    return addresses


class SensorBridge:
    def __init__(self):
        self.lock = threading.Lock()
        self.matrix = identity()
        self.raw = {}
        self.source = "sin sensores"
        self.last_at = 0.0
        self.queue = queue.Queue()
        self.running = True
        self.magnetic = None
        self.accel = None
        self.http_error = ""
        self.udp_error = ""
        self.filtered_euler = None
        self.filtered_at = 0.0
        self.motion = {}
        self.motion_at = 0.0

    def update(self, matrix, raw, source):
        with self.lock:
            self.matrix = matrix
            self.raw = raw
            self.source = source
            self.last_at = time.time()
        self.queue.put((source, raw))

    def update_from_payload(self, payload, source):
        if parse_motion_payload(payload, self):
            with self.lock:
                self.raw = payload
                self.source = source
                self.last_at = time.time()
            return

        matrix = parse_sensor_payload(payload, self)
        if matrix:
            self.update(matrix, payload, source)

    def snapshot(self):
        with self.lock:
            return self.matrix, dict(self.raw), self.source, self.last_at

    def motion_snapshot(self):
        with self.lock:
            return dict(self.motion), self.motion_at


def parse_sensor_payload(payload, bridge):
    if not isinstance(payload, dict):
        return None

    sensor_type = str(payload.get("type") or payload.get("sensor") or payload.get("name") or "").lower()
    values = payload.get("values") or payload.get("data")
    if isinstance(values, str):
        values = parse_numbers(values)
    elif isinstance(values, list):
        values = [to_float(value) for value in values if value is not None]
    else:
        values = []

    if all(key in payload for key in ("alpha", "beta", "gamma")):
        if payload.get("absolute") is True and str(payload.get("type", "")).lower() == "deviceorientation":
            return None
        alpha, beta, gamma = unwrap_euler(
            bridge,
            to_float(payload.get("alpha")),
            to_float(payload.get("beta")),
            to_float(payload.get("gamma")),
        )
        payload["alpha"] = alpha % 360.0
        payload["beta"] = beta
        payload["gamma"] = gamma
        return from_euler(alpha, beta, gamma)

    quaternion = payload.get("quaternion")
    if isinstance(quaternion, list) and len(quaternion) >= 4:
        x, y, z, w = [to_float(value) for value in quaternion[:4]]
        return quat_to_matrix(w, x, y, z)

    if ("rotation_vector" in sensor_type or "game_rotation_vector" in sensor_type) and len(values) >= 3:
        return rotation_vector_to_matrix(values)

    if "orientation" in sensor_type and len(values) >= 3:
        a, b, g = values[:3]
        if max(abs(a), abs(b), abs(g)) <= math.tau:
            a, b, g = math.degrees(a), math.degrees(b), math.degrees(g)
        return from_euler(a, b, g)

    if "accelerometer" in sensor_type or "gravity" in sensor_type:
        if len(values) >= 3:
            bridge.accel = values[:3]

    if "magnetic" in sensor_type or "magnetometer" in sensor_type:
        if len(values) >= 3:
            bridge.magnetic = values[:3]

    if bridge.accel:
        ax, ay, az = bridge.accel
        pitch = math.degrees(math.atan2(-ax, math.sqrt(ay * ay + az * az)))
        roll = math.degrees(math.atan2(ay, az))
        yaw = 0.0
        if bridge.magnetic:
            mx, my, _ = bridge.magnetic
            yaw = math.degrees(math.atan2(my, mx))
        return from_euler(yaw, pitch, roll)

    return None


def parse_motion_payload(payload, bridge):
    if not isinstance(payload, dict):
        return False

    if str(payload.get("type", "")).lower() != "devicemotion":
        return False

    acceleration = vector_dict(payload.get("acceleration"))
    gravity = vector_dict(payload.get("accelerationIncludingGravity"))
    rotation_rate = vector_dict(payload.get("rotationRate"))
    with bridge.lock:
        bridge.motion = {
            "acceleration": acceleration,
            "accelerationIncludingGravity": gravity,
            "rotationRate": rotation_rate,
            "interval": to_float(payload.get("interval")),
        }
        bridge.motion_at = time.time()
    return True


def vector_dict(value):
    if not isinstance(value, dict):
        return None
    return (
        to_float(value.get("x")),
        to_float(value.get("y")),
        to_float(value.get("z")),
    )


def to_float(value):
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def unwrap_euler(bridge, alpha, beta, gamma):
    now = time.time()
    if bridge.filtered_euler is None:
        bridge.filtered_euler = (alpha, beta, gamma)
        bridge.filtered_at = now
        return bridge.filtered_euler

    previous_alpha, previous_beta, previous_gamma = bridge.filtered_euler
    alpha = previous_alpha + shortest_angle_delta(previous_alpha, alpha)
    filtered = (alpha, beta, gamma)
    bridge.filtered_euler = filtered
    bridge.filtered_at = now
    return filtered


def shortest_angle_delta(previous, current):
    return (current - previous + 180.0) % 360.0 - 180.0


class BridgeRequestHandler(BaseHTTPRequestHandler):
    bridge = None

    def do_GET(self):
        route = urlparse(self.path).path
        if route in ("/", "/phone", "/phone.html"):
            try:
                body = PHONE_HTML.read_bytes()
            except OSError:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Permissions-Policy", "accelerometer=*, gyroscope=*, magnetometer=*")
            self.send_header("Feature-Policy", "accelerometer *; gyroscope *; magnetometer *")
            self.end_headers()
            self.wfile.write(body)
            return

        if route == "/status":
            _, raw, source, last_at = self.bridge.snapshot()
            body = json.dumps({"source": source, "age": time.time() - last_at, "raw": raw}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_error(404)

    def do_POST(self):
        route = urlparse(self.path).path
        if route != "/sensor":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode("utf-8"))
            self.bridge.update_from_payload(payload, "navegador movil")
            self.send_response(204)
            self.end_headers()
        except json.JSONDecodeError:
            self.send_error(400)

    def log_message(self, *_args):
        return


def run_http_server(bridge):
    BridgeRequestHandler.bridge = bridge
    try:
        server = ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), BridgeRequestHandler)
        server.serve_forever()
    except OSError as error:
        bridge.http_error = str(error)


def run_udp_server(bridge):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("0.0.0.0", UDP_PORT))
    except OSError as error:
        bridge.udp_error = str(error)
        return
    sock.settimeout(0.5)
    while bridge.running:
        try:
            data, addr = sock.recvfrom(8192)
        except socket.timeout:
            continue
        except OSError:
            break
        text = data.decode("utf-8", errors="ignore").strip()
        payload = parse_udp_text(text)
        if payload:
            bridge.update_from_payload(payload, f"UDP {addr[0]}")


def parse_udp_text(text):
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    numbers = parse_numbers(text)

    if len(numbers) >= 5:
        sensor_code = int(numbers[1]) if abs(numbers[1] - round(numbers[1])) < 0.001 else int(numbers[0])
        values = numbers[-4:] if sensor_code in (11, 15) else numbers[-3:]
        type_name = {
            1: "android.sensor.accelerometer",
            2: "android.sensor.magnetic_field",
            3: "android.sensor.orientation",
            4: "android.sensor.gyroscope",
            9: "android.sensor.gravity",
            11: "android.sensor.rotation_vector",
            15: "android.sensor.game_rotation_vector",
        }.get(sensor_code, "orientation")
        return {"type": type_name, "values": values}
    if len(numbers) >= 4:
        return {"type": "android.sensor.rotation_vector", "values": numbers[:4]}
    if len(numbers) >= 3:
        return {"type": "orientation", "values": numbers[:3]}
    return None


def parse_numbers(text):
    cleaned = text.replace(";", ",").replace("\t", ",").replace(" ", ",")
    numbers = []
    for part in cleaned.split(","):
        if not part:
            continue
        try:
            numbers.append(float(part))
        except ValueError:
            continue
    return numbers


class RedmiModel:
    def __init__(self):
        self.height = 161.15
        self.width = 74.24
        self.depth = 7.98
        self.radius = 8.0
        self.boundary = self._rounded_boundary(self.width / 2, self.height / 2, self.radius, 7)
        self.vertices = []
        self.faces = []
        self._build_body()

    def _rounded_boundary(self, hw, hh, radius, segments):
        points = []
        centers = (
            (hw - radius, hh - radius, 0.0, math.pi / 2),
            (-hw + radius, hh - radius, math.pi / 2, math.pi),
            (-hw + radius, -hh + radius, math.pi, math.pi * 1.5),
            (hw - radius, -hh + radius, math.pi * 1.5, math.tau),
        )
        for cx, cy, start, end in centers:
            for step in range(segments + 1):
                angle = start + (end - start) * step / segments
                points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
        return points

    def _build_body(self):
        half_depth = self.depth / 2
        front = []
        back = []
        for x, y in self.boundary:
            back.append(len(self.vertices))
            self.vertices.append((x, y, -half_depth))
            front.append(len(self.vertices))
            self.vertices.append((x, y, half_depth))

        self.faces.append({"points": back[::-1], "fill": "#12161c", "outline": "#2e3640", "kind": "back"})
        self.faces.append({"points": front, "fill": "#05070a", "outline": "#8ea0ad", "kind": "front"})

        count = len(self.boundary)
        for index in range(count):
            a_back = index * 2
            a_front = a_back + 1
            b_back = ((index + 1) % count) * 2
            b_front = b_back + 1
            self.faces.append(
                {
                    "points": [a_back, b_back, b_front, a_front],
                    "fill": "#202833",
                    "outline": "#394451",
                    "kind": "side",
                }
            )


class TwinApp:
    def __init__(self):
        self.bridge = SensorBridge()
        self.model = RedmiModel()
        self.root = tk.Tk()
        self.root.title("Redmi Note 13 Pro - gemelo digital local")
        self.root.geometry("1180x760")
        self.root.minsize(900, 620)
        self.canvas = tk.Canvas(self.root, bg="#07090d", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.object_matrix = identity()
        self.target_matrix = mat_mul(rot_x(math.radians(-18)), rot_z(math.radians(-18)))
        self.calibration = identity()
        self.sensor_enabled = True
        self.zoom = 4.15
        self.view_yaw = math.radians(-24)
        self.view_pitch = math.radians(-14)
        self.orthographic = True
        self.drag_start = None
        self.last_frame = time.time()
        self.last_raw = {}
        self.position = (0.0, 0.0, 0.0)
        self.velocity = (0.0, 0.0, 0.0)
        self.accel_bias = (0.0, 0.0, 0.0)
        self.filtered_accel = (0.0, 0.0, 0.0)
        self.last_motion_at = 0.0
        self.last_motion_vector = (0.0, 0.0, 0.0)
        self.motion_enabled = True

        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        self.root.bind("<Key-c>", lambda _event: self.calibrate())
        self.root.bind("<Key-r>", lambda _event: self.reset_calibration())
        self.root.bind("<Key-x>", lambda _event: self.reset_translation())
        self.root.bind("<Key-m>", lambda _event: self.toggle_motion())
        self.root.bind("<Key-space>", lambda _event: self.toggle_sensor())
        self.root.bind("<Key-p>", lambda _event: self.toggle_projection())
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        threading.Thread(target=run_http_server, args=(self.bridge,), daemon=True).start()
        threading.Thread(target=run_udp_server, args=(self.bridge,), daemon=True).start()

    def run(self):
        self.animate()
        self.root.mainloop()

    def close(self):
        self.bridge.running = False
        self.root.destroy()

    def on_drag_start(self, event):
        self.drag_start = (event.x, event.y, self.view_yaw, self.view_pitch)

    def on_drag(self, event):
        if not self.drag_start:
            return
        x0, y0, yaw0, pitch0 = self.drag_start
        self.view_yaw = yaw0 + (event.x - x0) * 0.008
        self.view_pitch = clamp(pitch0 + (event.y - y0) * 0.008, math.radians(-80), math.radians(80))

    def on_wheel(self, event):
        direction = 1 if event.delta > 0 else -1
        self.zoom = clamp(self.zoom * (1.08 if direction > 0 else 0.92), 2.5, 16.0)

    def calibrate(self):
        matrix, _raw, _source, _last_at = self.bridge.snapshot()
        self.calibration = transpose(matrix)

    def reset_calibration(self):
        self.calibration = identity()

    def toggle_sensor(self):
        self.sensor_enabled = not self.sensor_enabled

    def toggle_projection(self):
        self.orthographic = not self.orthographic

    def reset_translation(self):
        self.position = (0.0, 0.0, 0.0)
        self.velocity = (0.0, 0.0, 0.0)
        self.accel_bias = (0.0, 0.0, 0.0)
        self.filtered_accel = (0.0, 0.0, 0.0)

    def toggle_motion(self):
        self.motion_enabled = not self.motion_enabled
        if not self.motion_enabled:
            self.reset_translation()

    def animate(self):
        now = time.time()
        dt = min(0.05, now - self.last_frame)
        self.last_frame = now

        matrix, raw, source, last_at = self.bridge.snapshot()
        motion, motion_at = self.bridge.motion_snapshot()
        connected = now - last_at < 5.0
        if self.sensor_enabled and connected:
            self.target_matrix = mat_mul(self.calibration, matrix)
            self.last_raw = raw
        elif not connected and self.sensor_enabled and not self.last_raw:
            self.target_matrix = mat_mul(rot_x(math.radians(-18)), rot_z(math.radians(-18)))

        self.apply_motion(dt, motion, motion_at)
        self.object_matrix = lerp_matrix(self.object_matrix, self.target_matrix, min(1.0, dt * 18.0))
        self.draw(source, connected)
        self.root.after(16, self.animate)

    def apply_motion(self, dt, motion, motion_at):
        if not self.sensor_enabled or not self.motion_enabled or time.time() - motion_at > 0.5:
            self.velocity = scale_vec(self.velocity, max(0.0, 1.0 - dt * 2.4))
            self.position = scale_vec(self.position, max(0.0, 1.0 - dt * 0.18))
            return

        acceleration = motion.get("acceleration")
        gravity_acceleration = motion.get("accelerationIncludingGravity")
        if not acceleration or vec_len(acceleration) < 0.01:
            if not gravity_acceleration:
                return
            bias_amount = min(1.0, dt * 0.35)
            self.accel_bias = lerp_vec(self.accel_bias, gravity_acceleration, bias_amount)
            acceleration = sub_vec(gravity_acceleration, self.accel_bias)

        self.filtered_accel = lerp_vec(self.filtered_accel, acceleration, min(1.0, dt * 18.0))
        acceleration = self.filtered_accel

        accel_magnitude = vec_len(acceleration)
        if accel_magnitude < 0.035:
            acceleration = (0.0, 0.0, 0.0)

        self.last_motion_vector = acceleration
        world_acceleration = mat_vec(self.object_matrix, acceleration)
        visual_acceleration = scale_vec(world_acceleration, 145.0)
        damping_rate = 0.65 if accel_magnitude >= 0.08 else 7.5
        spring_rate = 0.16 if accel_magnitude >= 0.08 else 1.1
        spring = scale_vec(self.position, -spring_rate)
        damping = scale_vec(self.velocity, -damping_rate)
        total_acceleration = add_vec(add_vec(visual_acceleration, spring), damping)
        self.velocity = add_vec(self.velocity, scale_vec(total_acceleration, dt))
        self.velocity = (
            clamp(self.velocity[0], -180.0, 180.0),
            clamp(self.velocity[1], -220.0, 220.0),
            clamp(self.velocity[2], -150.0, 150.0),
        )
        self.position = add_vec(self.position, scale_vec(self.velocity, dt))
        self.position = (
            clamp(self.position[0], -145.0, 145.0),
            clamp(self.position[1], -175.0, 175.0),
            clamp(self.position[2], -120.0, 120.0),
        )
        self.velocity = (
            0.0 if abs(self.position[0]) >= 145.0 else self.velocity[0],
            0.0 if abs(self.position[1]) >= 175.0 else self.velocity[1],
            0.0 if abs(self.position[2]) >= 120.0 else self.velocity[2],
        )

    def view_matrix(self):
        return mat_mul(rot_x(self.view_pitch), rot_y(self.view_yaw))

    def transform(self, point):
        rotated = mat_vec(self.object_matrix, point)
        moved = add_vec(rotated, self.position)
        return mat_vec(self.view_matrix(), moved)

    def project(self, point):
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        z = point[2]
        depth_scale = clamp(1.0 + self.position[2] / 260.0, 0.58, 1.55)
        if self.orthographic:
            scale = self.zoom * depth_scale
        else:
            focal = 900.0
            scale = self.zoom * focal / max(120.0, focal + z + 220.0)
        return (width * 0.52 + point[0] * scale, height * 0.51 - point[1] * scale, z)

    def draw(self, source, connected):
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        self.draw_background(width, height)
        self.draw_translation_bounds(width, height)

        transformed = [self.transform(vertex) for vertex in self.model.vertices]
        projected = [self.project(vertex) for vertex in transformed]
        faces = []
        for face in self.model.faces:
            depth = sum(transformed[index][2] for index in face["points"]) / len(face["points"])
            faces.append((depth, face))

        for _depth, face in sorted(faces):
            points = []
            for index in face["points"]:
                points.extend(projected[index][:2])
            shade = self.face_shade(face, transformed)
            self.canvas.create_polygon(points, fill=shade, outline=face["outline"], width=1.2)

        self.draw_features(projected, transformed)
        self.draw_position_marker(width, height)
        self.draw_hud(width, height, source, connected)

    def face_shade(self, face, transformed):
        base = face["fill"]
        if face["kind"] == "front":
            return "#05070a"
        if face["kind"] == "back":
            return "#15191f"
        return base

    def draw_background(self, width, height):
        for index in range(0, height, 4):
            t = index / max(1, height)
            r = int(7 + 12 * t)
            g = int(9 + 14 * t)
            b = int(13 + 19 * t)
            self.canvas.create_rectangle(0, index, width, index + 4, outline="", fill=f"#{r:02x}{g:02x}{b:02x}")
        cx = width * 0.52
        cy = height * 0.74
        for i in range(-12, 13):
            self.canvas.create_line(cx - 520, cy + i * 22, cx + 520, cy + i * 22, fill="#1b2732")
            self.canvas.create_line(cx + i * 42, cy - 260, cx + i * 42, cy + 260, fill="#15202a")

    def draw_translation_bounds(self, width, height):
        cx = width * 0.52
        cy = height * 0.51
        self.canvas.create_rectangle(cx - 540, cy - 340, cx + 540, cy + 340, outline="#253849", width=1, dash=(6, 6))
        self.canvas.create_line(cx - 380, cy, cx + 380, cy, fill="#203445")
        self.canvas.create_line(cx, cy - 250, cx, cy + 250, fill="#203445")

    def draw_position_marker(self, width, height):
        x, y, z = self.position
        cx = width * 0.52
        cy = height * 0.51
        px = cx + x * self.zoom
        py = cy - y * self.zoom
        self.canvas.create_oval(px - 5, py - 5, px + 5, py + 5, fill="#7dd3fc", outline="")
        self.canvas.create_line(cx, cy, px, py, fill="#7dd3fc", width=1.4)
        depth_label = "adelante" if z > 5 else "atras" if z < -5 else "centro"
        self.canvas.create_text(px + 10, py - 12, anchor="w", text=f"XYZ {x:.0f},{y:.0f},{z:.0f} | Z {depth_label}", fill="#9be7ff", font=("Consolas", 9))

    def draw_features(self, projected, transformed):
        front_normal = mat_vec(self.view_matrix(), mat_vec(self.object_matrix, (0.0, 0.0, 1.0)))
        front_visible = front_normal[2] > 0.0
        if front_visible:
            self.draw_front_details()
        else:
            self.draw_back_details()

    def plane_point(self, x, y, z):
        return self.project(self.transform((x, y, z)))[:2]

    def plane_polygon(self, x, y, w, h, z, radius=0.0, segments=5):
        hw, hh = w / 2, h / 2
        if radius <= 0:
            pts = ((x - hw, y - hh, z), (x + hw, y - hh, z), (x + hw, y + hh, z), (x - hw, y + hh, z))
        else:
            boundary = self.model._rounded_boundary(hw, hh, radius, segments)
            pts = tuple((x + px, y + py, z) for px, py in boundary)
        out = []
        for point in pts:
            out.extend(self.project(self.transform(point))[:2])
        return out

    def plane_circle(self, x, y, radius, z, segments=32):
        out = []
        for i in range(segments):
            angle = math.tau * i / segments
            point = (x + math.cos(angle) * radius, y + math.sin(angle) * radius, z)
            out.extend(self.project(self.transform(point))[:2])
        return out

    def draw_front_details(self):
        z = self.model.depth / 2 + 0.22
        self.canvas.create_polygon(self.plane_polygon(0, 0, 66, 150, z, 5), fill="#05070a", outline="#99a6b1", width=1.3)
        self.canvas.create_polygon(self.plane_polygon(0, 0, 60, 140, z + 0.05, 3), fill="#061321", outline="")
        self.canvas.create_polygon(self.plane_polygon(-15, 18, 28, 82, z + 0.06, 2), fill="#123651", outline="")
        self.canvas.create_polygon(self.plane_polygon(16, -26, 25, 66, z + 0.06, 2), fill="#121b31", outline="")
        self.canvas.create_polygon(self.plane_polygon(0, -61, 48, 12, z + 0.08, 2), fill="#0e2335", outline="#203d50")
        self.canvas.create_polygon(self.plane_circle(0, 69, 2.2, z + 0.11, 24), fill="#0b0d10", outline="#3b4650")
        self.canvas.create_polygon(self.plane_polygon(0, 74.5, 17, 1.4, z + 0.1, 0.7), fill="#24313a", outline="")
        self.canvas.create_polygon(self.plane_polygon(0, 0, 22, 122, z + 0.09, 2), fill="#ffffff", outline="")

    def draw_back_details(self):
        z = -self.model.depth / 2 - 0.25
        self.canvas.create_polygon(self.plane_polygon(0, 0, 69, 151, z, 6), fill="#d7eee7", outline="#8aa59c", width=1.4)
        self.canvas.create_polygon(self.plane_polygon(-16, 47, 35, 54, z - 0.1, 5), fill="#e9f4f0", outline="#8da49c", width=1.6)
        self.canvas.create_polygon(self.plane_polygon(15, -8, 26, 126, z - 0.06, 5), fill="#c7e2da", outline="")
        self.canvas.create_polygon(self.plane_polygon(-21, 47, 18, 48, z - 0.14, 4), fill="#f6fbf9", outline="")
        self.canvas.create_polygon(self.plane_circle(-25, 60, 8.4, z - 0.22), fill="#050607", outline="#68727b", width=2.2)
        self.canvas.create_polygon(self.plane_circle(-25, 60, 5.2, z - 0.28), fill="#101820", outline="#1f2f3a", width=1.2)
        self.canvas.create_polygon(self.plane_circle(-25, 60, 2.0, z - 0.34), fill="#8fb8ca", outline="")
        self.canvas.create_polygon(self.plane_circle(-8, 60, 5.4, z - 0.18), fill="#080b0d", outline="#74818d", width=1.4)
        self.canvas.create_polygon(self.plane_circle(-25, 39, 5.9, z - 0.18), fill="#080b0d", outline="#74818d", width=1.4)
        self.canvas.create_polygon(self.plane_circle(-8, 39, 3.4, z - 0.18), fill="#f5d47c", outline="#806f3a", width=1)
        self.canvas.create_text(*self.plane_point(-16.5, 23, z - 0.24), text="200MP", fill="#5c6c72", font=("Segoe UI", 7, "bold"))
        self.canvas.create_text(*self.plane_point(5, -51, z - 0.16), text="Redmi", fill="#6d817c", font=("Segoe UI", 13, "bold"))
        self.canvas.create_text(*self.plane_point(5, -61, z - 0.16), text="5G", fill="#8da09a", font=("Segoe UI", 7, "bold"))

    def draw_hud(self, width, height, source, connected):
        status = "recibiendo sensores" if connected else "esperando sensores"
        color = "#2dd46f" if connected else "#f59e0b"
        projection = "ortografica CAD" if self.orthographic else "perspectiva"
        self.canvas.create_text(24, 24, anchor="nw", text="Redmi Note 13 Pro - gemelo digital local", fill="#f4f7fb", font=("Segoe UI", 18, "bold"))
        self.canvas.create_oval(26, 64, 38, 76, fill=color, outline="")
        self.canvas.create_text(48, 61, anchor="nw", text=f"{status} | fuente: {source} | vista: {projection}", fill="#dce6ef", font=("Segoe UI", 11))
        self.canvas.create_text(24, height - 116, anchor="nw", text="Controles PC: arrastrar = orbitar camara | rueda = zoom | C = calibrar | R = reset | X = centrar XYZ | M = movimiento | P = proyeccion", fill="#aeb9c4", font=("Segoe UI", 10))
        self.canvas.create_text(24, height - 92, anchor="nw", text=f"HTTP movil: {self.phone_url()}   UDP sensores: {self.first_ip()}:{UDP_PORT}", fill="#8fd3ff", font=("Consolas", 10))
        if self.last_raw:
            values = []
            for key in ("alpha", "beta", "gamma"):
                if key in self.last_raw:
                    values.append(f"{key}={float(self.last_raw[key]):.1f}")
            if self.last_motion_vector:
                ax, ay, az = self.last_motion_vector
                values.append(f"acc=({ax:.2f},{ay:.2f},{az:.2f})")
                px, py, pz = self.position
                values.append(f"pos=({px:.1f},{py:.1f},{pz:.1f})")
            if values:
                self.canvas.create_text(24, height - 66, anchor="nw", text=" | ".join(values), fill="#f0f6fb", font=("Consolas", 10))
        if self.bridge.http_error or self.bridge.udp_error:
            error_text = f"HTTP: {self.bridge.http_error or 'ok'} | UDP: {self.bridge.udp_error or 'ok'}"
            self.canvas.create_text(24, height - 40, anchor="nw", text=error_text, fill="#ff8a8a", font=("Consolas", 10))

    def first_ip(self):
        addresses = get_lan_addresses()
        return addresses[0] if addresses else "IP_DEL_PC"

    def phone_url(self):
        return f"http://{self.first_ip()}:{HTTP_PORT}/phone"


if __name__ == "__main__":
    TwinApp().run()
