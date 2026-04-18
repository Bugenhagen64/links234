# mqtt_bridge.py

import json
import os
import time
import threading
import paho.mqtt.client as mqtt
import socket

from app.core.device_manager import DeviceManager
import app.core.db as db

MQTT_TOPIC_BASE = "display"
MQTT_STATUS_TOPIC = f"{MQTT_TOPIC_BASE}/status"
MQTT_COMMAND_TOPIC = f"{MQTT_TOPIC_BASE}/command/#"


class MQTTBridge:
    def __init__(self, host=None, port=None, username=None, password=None):
        self.host = host or os.getenv("MQTT_HOST", "central.avtjanst.com")
        self.port = port or int(os.getenv("MQTT_PORT", "1883"))
        self.username = username or os.getenv("MQTT_USERNAME")
        self.password = password or os.getenv("MQTT_PASSWORD")

        self.dm = DeviceManager()
        self.client = mqtt.Client()
        self.client.tls_set()

        # ⭐ Tvinga IPv4 (fixar ConnectionRefused på macOS)
        self.client.socket_options = [(socket.AF_INET, socket.SOCK_STREAM)]

        if username:
            self.client.username_pw_set(username, password)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        self.running = True

    # ---------------------------------------------------------
    #  MQTT callbacks
    # ---------------------------------------------------------

    def on_connect(self, client, userdata, flags, rc):
        print("MQTT connected:", rc)
        client.subscribe(MQTT_COMMAND_TOPIC)

    def on_disconnect(self, client, userdata, rc):
        print("MQTT disconnected:", rc)
        # Automatisk reconnect
        while self.running:
            try:
                print("Trying to reconnect...")
                client.reconnect()
                break
            except:
                time.sleep(2)

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8")

        print(f"MQTT RX: {topic} = {payload}")

        try:
            data = json.loads(payload)
        except:
            print("Invalid JSON")
            return

        # Kommandon
        if topic.startswith(f"{MQTT_TOPIC_BASE}/command/"):
            cmd = topic.split("/")[-1]
            self.handle_command(cmd, data)

    # ---------------------------------------------------------
    #  Command handler
    # ---------------------------------------------------------

    def handle_command(self, cmd, data):
        print("Handling command:", cmd, data)

        if cmd == "power":
            state = data.get("state")
            self.dm.set_power(state)

        elif cmd == "input":
            code = data.get("code")
            self.dm.set_input(code)

        elif cmd == "volume":
            delta = data.get("delta")
            self.dm.volume_change(delta)

        elif cmd == "mute":
            audio = data.get("audio")
            video = data.get("video")
            self.dm.set_mute(audio=audio, video=video)

        # Efter varje kommando → publicera status
        self.publish_status()

    # ---------------------------------------------------------
    #  Status publisher
    # ---------------------------------------------------------

    def publish_status(self):
        device = db.get_device()
        if not device:
            return

        status = db.get_status(device["id"])
        caps = db.get_capabilities(device["id"])
        inputs = db.get_inputs(device["id"])

        payload = {
            "device": dict(device),
            "status": dict(status) if status else None,
            "capabilities": dict(caps) if caps else None,
            "inputs": [dict(i) for i in inputs]
        }

        self.client.publish(MQTT_STATUS_TOPIC, json.dumps(payload), retain=True)
        print("MQTT TX:", payload)

    # ---------------------------------------------------------
    #  Background status loop
    # ---------------------------------------------------------

    def status_loop(self):
        while self.running:
            self.dm.get_status()
            self.publish_status()
            time.sleep(5)

    # ---------------------------------------------------------
    #  Start
    # ---------------------------------------------------------

    def start(self):
        print("Starting MQTT bridge...")

        self.client.connect(self.host, self.port, 60)

        # Starta status‑tråd
        t = threading.Thread(target=self.status_loop, daemon=True)
        t.start()

        # Blockera här
        self.client.loop_forever()


if __name__ == "__main__":
    bridge = MQTTBridge(
        host="localhost",
        port=1883,
        username=None,
        password=None
    )
    bridge.start()
