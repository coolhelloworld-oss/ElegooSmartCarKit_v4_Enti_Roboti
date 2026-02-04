#!/usr/bin/env python3
import argparse
import json
import socket
import time
import tkinter as tk
from tkinter import ttk

import cv2
from PIL import Image, ImageTk


COMMAND_MAP = {
    "forward": 1,
    "backward": 2,
    "left": 3,
    "right": 4,
    "left_forward": 5,
    "left_backward": 6,
    "right_forward": 7,
    "right_backward": 8,
    "stop": 9,
}


def build_command(seq, direction, speed):
    payload = {
        "N": 102,
        "D1": direction,
        "D2": speed,
        "H": f"ER{seq:04d}",
    }
    return json.dumps(payload, separators=(",", ":")) + "}"


def build_simple_command(seq, command, **data):
    payload = {"N": command, "H": f"ER{seq:04d}"}
    payload.update(data)
    return json.dumps(payload, separators=(",", ":")) + "}"


class WifiController:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.seq = 1

    def connect(self):
        if self.socket:
            return
        self.socket = socket.create_connection((self.host, self.port), timeout=3)
        time.sleep(0.2)

    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.socket = None

    def send(self, direction, speed):
        if not self.socket:
            return
        command = build_command(self.seq, direction, speed)
        self.socket.sendall(command.encode("utf-8"))
        self.seq += 1

    def send_command(self, command, **data):
        if not self.socket:
            return
        payload = build_simple_command(self.seq, command, **data)
        self.socket.sendall(payload.encode("utf-8"))
        self.seq += 1


class EntiRobotiRemote(tk.Tk):
    def __init__(self, controller, speed, camera_url):
        super().__init__()
        self.controller = controller
        self.speed = tk.IntVar(value=speed)
        self.servo_angle = tk.IntVar(value=90)
        self.status = tk.StringVar(value="Nicht verbunden")
        self.camera_url = camera_url
        self.video_capture = None
        self.video_label = None
        self.video_image = None

        self.title("Enti Roboti Fernbedienung")
        self.geometry("1120x680")
        self.configure(bg="#161c2d")
        self._configure_style()
        self._build_layout()
        self._bind_keys()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#161c2d")
        style.configure("Card.TFrame", background="#20283d")
        style.configure("TLabel", background="#161c2d", foreground="#f4f7ff")
        style.configure("Header.TLabel", font=("Helvetica", 18, "bold"))
        style.configure("Sub.TLabel", font=("Helvetica", 11))
        style.configure("TButton", font=("Helvetica", 11, "bold"), padding=8)
        style.configure("Control.TButton", font=("Helvetica", 12, "bold"))
        style.configure("Accent.TButton", background="#f4b740", foreground="#1a1f2f")

    def _build_layout(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=24, pady=(20, 8))
        ttk.Label(header, text="Enti Roboti", style="Header.TLabel").pack(side="left")
        ttk.Label(
            header,
            text="Spielzeug-Roboter Fernbedienung",
            style="Sub.TLabel",
        ).pack(side="left", padx=12)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=24, pady=16)

        camera_card = ttk.Frame(body, style="Card.TFrame")
        camera_card.pack(side="left", fill="both", expand=True, padx=(0, 12))
        ttk.Label(
            camera_card,
            text="Kamera",
            style="Header.TLabel",
        ).pack(anchor="w", padx=16, pady=(16, 8))

        self.video_label = ttk.Label(camera_card, background="#111522")
        self.video_label.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        control_card = ttk.Frame(body, style="Card.TFrame", width=360)
        control_card.pack(side="right", fill="y")

        ttk.Label(
            control_card,
            text="Steuerung",
            style="Header.TLabel",
        ).pack(anchor="w", padx=16, pady=(16, 8))

        status_frame = ttk.Frame(control_card, style="Card.TFrame")
        status_frame.pack(fill="x", padx=16, pady=(0, 12))
        ttk.Label(status_frame, text="Status:", style="Sub.TLabel").pack(
            side="left", padx=8, pady=8
        )
        ttk.Label(status_frame, textvariable=self.status, style="Sub.TLabel").pack(
            side="left"
        )

        connect_frame = ttk.Frame(control_card, style="Card.TFrame")
        connect_frame.pack(fill="x", padx=16, pady=(0, 12))
        ttk.Button(
            connect_frame, text="Verbinden", style="Accent.TButton", command=self._connect
        ).pack(side="left", padx=8, pady=8)
        ttk.Button(
            connect_frame, text="Trennen", command=self._disconnect
        ).pack(side="left", padx=8, pady=8)

        speed_frame = ttk.Frame(control_card, style="Card.TFrame")
        speed_frame.pack(fill="x", padx=16, pady=(0, 16))
        ttk.Label(speed_frame, text="Speed", style="Sub.TLabel").pack(
            anchor="w", padx=8, pady=(8, 0)
        )
        ttk.Scale(
            speed_frame,
            from_=0,
            to=255,
            orient="horizontal",
            variable=self.speed,
        ).pack(fill="x", padx=8, pady=(0, 8))

        button_frame = ttk.Frame(control_card, style="Card.TFrame")
        button_frame.pack(fill="x", padx=16, pady=(0, 16))

        grid = ttk.Frame(button_frame, style="Card.TFrame")
        grid.pack(padx=8, pady=8)

        ttk.Button(
            grid, text="↖", style="Control.TButton", command=lambda: self._send("left_forward")
        ).grid(row=0, column=0, padx=6, pady=6)
        ttk.Button(
            grid, text="↑", style="Control.TButton", command=lambda: self._send("forward")
        ).grid(row=0, column=1, padx=6, pady=6)
        ttk.Button(
            grid, text="↗", style="Control.TButton", command=lambda: self._send("right_forward")
        ).grid(row=0, column=2, padx=6, pady=6)
        ttk.Button(
            grid, text="←", style="Control.TButton", command=lambda: self._send("left")
        ).grid(row=1, column=0, padx=6, pady=6)
        ttk.Button(
            grid, text="■", style="Control.TButton", command=lambda: self._send("stop")
        ).grid(row=1, column=1, padx=6, pady=6)
        ttk.Button(
            grid, text="→", style="Control.TButton", command=lambda: self._send("right")
        ).grid(row=1, column=2, padx=6, pady=6)
        ttk.Button(
            grid, text="↙", style="Control.TButton", command=lambda: self._send("left_backward")
        ).grid(row=2, column=0, padx=6, pady=6)
        ttk.Button(
            grid, text="↓", style="Control.TButton", command=lambda: self._send("backward")
        ).grid(row=2, column=1, padx=6, pady=6)
        ttk.Button(
            grid, text="↘", style="Control.TButton", command=lambda: self._send("right_backward")
        ).grid(row=2, column=2, padx=6, pady=6)

        mode_frame = ttk.Frame(control_card, style="Card.TFrame")
        mode_frame.pack(fill="x", padx=16, pady=(0, 16))
        ttk.Label(mode_frame, text="Modi", style="Sub.TLabel").pack(
            anchor="w", padx=8, pady=(8, 4)
        )
        mode_buttons = ttk.Frame(mode_frame, style="Card.TFrame")
        mode_buttons.pack(padx=8, pady=(0, 8))
        ttk.Button(
            mode_buttons,
            text="Linie",
            command=lambda: self._send_mode(1),
        ).grid(row=0, column=0, padx=4, pady=4)
        ttk.Button(
            mode_buttons,
            text="Hindernis",
            command=lambda: self._send_mode(2),
        ).grid(row=0, column=1, padx=4, pady=4)
        ttk.Button(
            mode_buttons,
            text="Folgen",
            command=lambda: self._send_mode(3),
        ).grid(row=0, column=2, padx=4, pady=4)
        ttk.Button(
            mode_buttons,
            text="Standby",
            command=lambda: self._send_stop_mode(),
        ).grid(row=1, column=0, padx=4, pady=4)
        ttk.Button(
            mode_buttons,
            text="Programm",
            command=lambda: self._send_clear_program(),
        ).grid(row=1, column=1, padx=4, pady=4)

        servo_frame = ttk.Frame(control_card, style="Card.TFrame")
        servo_frame.pack(fill="x", padx=16, pady=(0, 16))
        ttk.Label(servo_frame, text="Servo", style="Sub.TLabel").pack(
            anchor="w", padx=8, pady=(8, 0)
        )
        ttk.Scale(
            servo_frame,
            from_=0,
            to=180,
            orient="horizontal",
            variable=self.servo_angle,
            command=lambda _val: self._send_servo(),
        ).pack(fill="x", padx=8, pady=(0, 8))

        light_frame = ttk.Frame(control_card, style="Card.TFrame")
        light_frame.pack(fill="x", padx=16, pady=(0, 16))
        ttk.Label(light_frame, text="Licht", style="Sub.TLabel").pack(
            anchor="w", padx=8, pady=(8, 4)
        )
        light_buttons = ttk.Frame(light_frame, style="Card.TFrame")
        light_buttons.pack(padx=8, pady=(0, 8))
        ttk.Button(
            light_buttons,
            text="Rot",
            command=lambda: self._send_light(255, 0, 0),
        ).grid(row=0, column=0, padx=4, pady=4)
        ttk.Button(
            light_buttons,
            text="Grün",
            command=lambda: self._send_light(0, 255, 0),
        ).grid(row=0, column=1, padx=4, pady=4)
        ttk.Button(
            light_buttons,
            text="Blau",
            command=lambda: self._send_light(0, 0, 255),
        ).grid(row=0, column=2, padx=4, pady=4)
        ttk.Button(
            light_buttons,
            text="Weiß",
            command=lambda: self._send_light(255, 255, 255),
        ).grid(row=1, column=0, padx=4, pady=4)
        ttk.Button(
            light_buttons,
            text="Aus",
            command=lambda: self._send_light(0, 0, 0),
        ).grid(row=1, column=1, padx=4, pady=4)

        bright_frame = ttk.Frame(control_card, style="Card.TFrame")
        bright_frame.pack(fill="x", padx=16, pady=(0, 16))
        ttk.Label(bright_frame, text="Helligkeit", style="Sub.TLabel").pack(
            anchor="w", padx=8, pady=(8, 4)
        )
        bright_buttons = ttk.Frame(bright_frame, style="Card.TFrame")
        bright_buttons.pack(padx=8, pady=(0, 8))
        ttk.Button(
            bright_buttons,
            text="Hell +",
            command=lambda: self._send_brightness(1),
        ).grid(row=0, column=0, padx=4, pady=4)
        ttk.Button(
            bright_buttons,
            text="Hell -",
            command=lambda: self._send_brightness(2),
        ).grid(row=0, column=1, padx=4, pady=4)

        help_frame = ttk.Frame(control_card, style="Card.TFrame")
        help_frame.pack(fill="x", padx=16, pady=(0, 16))
        ttk.Label(
            help_frame,
            text="Hotkeys: W/A/S/D, Q/E/Z/C, X (Stop)",
            style="Sub.TLabel",
        ).pack(anchor="w", padx=8, pady=8)

    def _bind_keys(self):
        self.bind("<w>", lambda _e: self._send("forward"))
        self.bind("<s>", lambda _e: self._send("backward"))
        self.bind("<a>", lambda _e: self._send("left"))
        self.bind("<d>", lambda _e: self._send("right"))
        self.bind("<q>", lambda _e: self._send("left_forward"))
        self.bind("<e>", lambda _e: self._send("right_forward"))
        self.bind("<z>", lambda _e: self._send("left_backward"))
        self.bind("<c>", lambda _e: self._send("right_backward"))
        self.bind("<x>", lambda _e: self._send("stop"))

    def _connect(self):
        try:
            self.controller.connect()
            self.status.set("Verbunden")
            self._start_camera()
        except (OSError, socket.timeout):
            self.status.set("Verbindung fehlgeschlagen")

    def _disconnect(self):
        self.controller.disconnect()
        self.status.set("Getrennt")
        self._stop_camera()

    def _send(self, action):
        direction = COMMAND_MAP[action]
        self.controller.send(direction, self.speed.get())

    def _send_mode(self, mode):
        self.controller.send_command(101, D1=mode)

    def _send_stop_mode(self):
        self.controller.send_command(100)

    def _send_clear_program(self):
        self.controller.send_command(110)

    def _send_servo(self):
        self.controller.send_command(5, D1=1, D2=self.servo_angle.get())

    def _send_light(self, red, green, blue):
        self.controller.send_command(8, D1=0, D2=red, D3=green, D4=blue)

    def _send_brightness(self, direction):
        self.controller.send_command(105, D1=direction)

    def _start_camera(self):
        if self.video_capture:
            return
        camera_source = self.camera_url
        if isinstance(camera_source, str) and camera_source.isdigit():
            camera_source = int(camera_source)
        self.video_capture = cv2.VideoCapture(camera_source)
        self._update_camera()

    def _stop_camera(self):
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None
        if self.video_label:
            self.video_label.configure(image="")

    def _update_camera(self):
        if not self.video_capture:
            return
        ret, frame = self.video_capture.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (640, 360))
            image = Image.fromarray(frame)
            self.video_image = ImageTk.PhotoImage(image)
            self.video_label.configure(image=self.video_image)
        self.after(30, self._update_camera)

    def _on_close(self):
        self._stop_camera()
        self.controller.disconnect()
        self.destroy()


def main():
    parser = argparse.ArgumentParser(
        description="GUI-Fernbedienung für Enti Roboti über WLAN mit Kamera-Preview."
    )
    parser.add_argument("--host", required=True, help="IP/Hostname des Roboters")
    parser.add_argument("--port", type=int, default=100, help="TCP-Port (default: 100)")
    parser.add_argument("--camera-url", default="0", help="Kamera-Stream-URL oder Index")
    parser.add_argument("--speed", type=int, default=150, help="Startgeschwindigkeit 0-255")
    args = parser.parse_args()

    controller = WifiController(args.host, args.port)
    app = EntiRobotiRemote(
        controller,
        speed=max(0, min(255, args.speed)),
        camera_url=args.camera_url,
    )
    app.mainloop()


if __name__ == "__main__":
    main()
