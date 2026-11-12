import os
import sys
import time
import threading
import queue
import secrets
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

import requests

# Replace this with your deployed Render URL after deployment.
SERVER_URL = "https://YOUR-APP-NAME.onrender.com"

APP_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "ScreenShare"
DEVICE_FILE = APP_DIR / "device_id.txt"

def get_device_id():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    if DEVICE_FILE.exists():
        value = DEVICE_FILE.read_text(encoding="utf-8").strip()
        if len(value) == 32:
            return value
    value = secrets.token_hex(16)
    DEVICE_FILE.write_text(value, encoding="utf-8")
    return value

class ScreenShareClient:
    def __init__(self, root):
        self.root = root
        self.root.title("ScreenShare - Consent Client")
        self.root.geometry("430x270")
        self.root.resizable(False, False)
        self.device_id = get_device_id()
        self.events = queue.Queue()
        self.running = True

        tk.Label(root, text="ScreenShare", font=("Segoe UI", 22, "bold")).pack(pady=(18, 5))
        tk.Label(root, text="This computer can receive screen-viewing requests.", wraplength=370).pack(pady=4)
        tk.Label(root, text="Your device pairing ID:", font=("Segoe UI", 9, "bold")).pack(pady=(12, 2))
        self.id_entry = tk.Entry(root, width=39, justify="center")
        self.id_entry.insert(0, self.device_id)
        self.id_entry.configure(state="readonly")
        self.id_entry.pack()
        self.status = tk.Label(root, text="Waiting for a request…", fg="#2563eb")
        self.status.pack(pady=15)
        tk.Button(root, text="Quit", command=self.close, width=12).pack()
        tk.Label(root, text="Screen sharing starts only after you approve and choose a screen.",
                 font=("Segoe UI", 8), wraplength=380).pack(pady=10)

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        threading.Thread(target=self.poll_loop, daemon=True).start()
        self.root.after(300, self.process_events)

    def poll_loop(self):
        while self.running:
            try:
                if "YOUR-APP-NAME" not in SERVER_URL:
                    self.events.put(("status", "Set SERVER_URL in client.py first."))
                    time.sleep(4)
                    continue
                response = requests.get(
                    f"{SERVER_URL}/api/poll/{self.device_id}", timeout=12
                )
                if response.ok:
                    data = response.json()
                    if data.get("status") == "pending":
                        self.events.put(("request", data["request_id"]))
                        time.sleep(8)
                    else:
                        time.sleep(3)
                else:
                    self.events.put(("status", "Server unavailable; retrying…"))
                    time.sleep(6)
            except requests.RequestException:
                self.events.put(("status", "Connecting to server…"))
                time.sleep(6)

    def process_events(self):
        if not self.running:
            return
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "status":
                    self.status.config(text=value)
                elif kind == "request":
                    self.handle_request(value)
        except queue.Empty:
            pass
        self.root.after(300, self.process_events)

    def handle_request(self, request_id):
        answer = messagebox.askyesno(
            "ScreenShare connection request",
            "Someone is requesting permission to VIEW this computer's screen.\n\n"
            "Allow this request?\n\n"
            "No screen is shared unless you approve and then choose a screen."
        )
        decision = "allow" if answer else "deny"
        try:
            response = requests.post(
                f"{SERVER_URL}/api/respond/{request_id}",
                json={"device_id": self.device_id, "decision": decision},
                timeout=12
            )
            if response.ok and answer:
                self.status.config(text="Approved. Open the sharing window and choose a screen.")
                webbrowser.open(f"{SERVER_URL}/share/{request_id}")
            elif response.ok:
                self.status.config(text="Request denied.")
            else:
                self.status.config(text="Could not send your decision.")
        except requests.RequestException:
            self.status.config(text="Could not reach the server to send your decision.")

    def close(self):
        self.running = False
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenShareClient(root)
    root.mainloop()
