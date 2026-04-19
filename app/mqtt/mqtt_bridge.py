# mqtt_bridge.py

import json
import os
import time
import threading
import socket

import paho.mqtt.client as mqtt

from app.core.device_manager import DeviceManager
import app.core.db as db

MQTT_TOPIC_BASE = "display"
MQTT_STATUS_TOPIC = f"{MQTT_TOPIC_BASE}/status"
MQTT_COMMAND_TOPIC = f"{MQTT_TOPIC_BASE}/command/#"
MQTT_INPUTS_TOPIC = f"{MQTT_TOPIC_BASE}/inputs"   # <-- nytt: separat inputs-topic


class MQTTBridge:
    def __init__(self, host=None, port=None, username=None, password=None):
        self.host = host or os.getenv("MQTT_HOST", "central.avtjanst.com")
        self.port = port or int(os.getenv("MQTT_PORT", "1883"))
        self.username = username or os.getenv("MQTT_USERNAME")
        self.password = password or os.getenv("MQTT_PASSWORD")

        self.dm = DeviceManager()
        self.client = mqtt.Client()

        # Tvinga IPv4 (fixar vissa miljöproblem)
        self.client.socket_options = [(socket.AF_INET, socket.SOCK_STREAM)]

        if self.username:
            self.client.username_pw_set(self.username, self.password)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        self.running = True
        self.polling = False

        # Poll-cache. 
        self.enable_poll_cache = False
        self._last_payload = None

    # ---------------------------------------------------------
    #  MQTT callbacks
    # ---------------------------------------------------------

    def on_connect(self, client, userdata, flags, rc):
        print("MQTT connected:", rc)
        client.subscribe(MQTT_COMMAND_TOPIC)
        # Publicera status direkt vid connect
        self.publish_status()
        # Publicera även inputs direkt (så panel kan läsa utan att fråga)
        self.publish_inputs()

    def on_disconnect(self, client, userdata, rc):
        print("MQTT disconnected:", rc)
        # Enkel automatisk reconnect
        while self.running:
            try:
                print("Trying to reconnect...")
                client.reconnect()
                break
            except Exception as e:
                print("Reconnect failed:", e)
                time.sleep(2)

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8")

        print(f"MQTT RX: {topic} = {payload}")

        try:
            data = json.loads(payload)
        except Exception:
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

        elif cmd == "inputs_get":
            # Panelen ber uttryckligen om inputs
            self.publish_inputs()
            return

        elif cmd == "status_get":
            # Panelen ber uttryckligen om status
            self.publish_status()
            return

        # Efter varje "state change"-kommando → publicera status
        self.publish_status()

    # ---------------------------------------------------------
    #  Status / inputs payloads
    # ---------------------------------------------------------

    def build_payload(self):
        device = db.get_device()
        if not device:
            return None

        status = db.get_status(device["id"])
        caps = db.get_capabilities(device["id"])
        inputs = db.get_inputs(device["id"])

        payload = {
            "device": device,
            "status": status if status else None,
            "capabilities": caps if caps else [],
            "inputs": inputs if inputs else [],
        }
        return payload

    def build_inputs_payload(self):
        device = db.get_device()
        if not device:
            return None

        inputs = db.get_inputs(device["id"])
        return {
            "device_id": device["id"],
            "inputs": inputs if inputs else [],
        }

    # ---------------------------------------------------------
    #  Publishers
    # ---------------------------------------------------------

    def publish_status(self):
        payload = self.build_payload()
        if not payload:
            print("No device configured, not publishing status.")
            return

        # Poll-cache: skicka bara om payload ändrats
        if self.enable_poll_cache:
            if payload == self._last_payload:
                # Ingen förändring → inget att skicka
                return
            self._last_payload = payload

        self.client.publish(MQTT_STATUS_TOPIC, json.dumps(payload), retain=True)
        print("MQTT TX status:", payload)

    def publish_inputs(self):
        payload = self.build_inputs_payload()
        if not payload:
            print("No device configured, not publishing inputs.")
            return

        self.client.publish(MQTT_INPUTS_TOPIC, json.dumps(payload), retain=True)
        print("MQTT TX inputs:", payload)

    def safe_poll_status(self):
        if self.polling:
            return  # En poll pågår redan

        self.polling = True
        try:
            self.dm.get_status()
            self.publish_status()
        finally:
            self.polling = False


    # ---------------------------------------------------------
    #  Background status loop
    # ---------------------------------------------------------

    def status_loop(self):
        # Vänta innan första poll
        time.sleep(30)

        while self.running:
            if not self.polling:
                # Kör poll i egen tråd så MQTT-loop inte blockeras
                threading.Thread(target=self.safe_poll_status, daemon=True).start()

            time.sleep(30)  # <-- nytt intervall


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
        password=None,
    )
    # Poll cache - enable:a detta när allt är klart. 
    # Det gör så att det endast publceras info när något förändrats.
    bridge.enable_poll_cache = False
    bridge.start()
