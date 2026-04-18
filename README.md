✔ Kör CLI:
python -m app.cli.cli setup --host 192.168.1.50 --port 4352

✔ Kör MQTT‑bridge:
python -m app.mqtt.mqtt_bridge

✔ Kör status:
python -m app.cli.cli status

✔ Kör power:
python -m app.cli.cli power on

✔ Byt input:
python3 -m app.cli.cli input hdmi1

✔ Höj volymen:
python3 -m app.cli.cli volume +5

✔ Mute:a ljudet:
python3 -m app.cli.cli mute audio


Skapa en enhet till fake_driver
-------------------------------
python3 - << 'EOF'
from app.core import db
db.save_device({
    "protocol": "fake",
    "host": "127.0.0.1",
    "port": 1234,
    "serial_port": None
})
print("Fake device added.")
EOF
-------------------------------
