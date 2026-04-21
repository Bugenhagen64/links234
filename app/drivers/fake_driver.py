# fake_driver.py
#
# En enkel test‑driver som simulerar en display/projektor.
# Används för utveckling utan hårdvara.

# ---------------------------------------------------------
#  Capabilities
# ---------------------------------------------------------

capabilities = ["power", "input", "volume", "mute"]

# ---------------------------------------------------------
#  Inputs
# ---------------------------------------------------------

inputs = [
    {"name": "HDMI 1", "code": "31"},
    {"name": "HDMI 2", "code": "32"},
    {"name": "RGB 1", "code": "11"},
    {"name": "Video", "code": "21"},
]

# ---------------------------------------------------------
#  Discovery (gemensam för både serial och network)
# ---------------------------------------------------------

def _base_discovery():
    """
    Returnerar capabilities, inputs, initial status,
    samt märke och modell.
    """
    return {
        "capabilities": capabilities,
        "inputs": inputs,
        "status": {
            "power": "off",
            "input": "31",
            "volume": 10,
            "audio_mute": False,
            "video_mute": False,

            # Lägg till lampor
            "lamps": [
                {"hours": 1235, "on": False}
            ],

            # Lägg till felstatus
            "errors": {
                "fan": "0",
                "lamp": "0",
                "temperature": "0",
                "cover": "0",
                "filter": "0",
                "other": "0"
            }
        },
        "manufacturer": "FakeCo",
        "model": "VirtualDisplay 9000",
    }

def discover_serial(port):
    # Fake: port ignoreras
    return _base_discovery()

def discover_net(host, port):
    # Fake: host/port ignoreras
    return _base_discovery()

# ---------------------------------------------------------
#  Status
# ---------------------------------------------------------

def get_status(device):
    """
    Fake-status hämtas från DB.
    """
    import app.core.db as db
    return db.get_status(device["id"])

# ---------------------------------------------------------
#  Power
# ---------------------------------------------------------

def set_power(device, state):
    import app.core.db as db
    db.update_status_field(device["id"], "power", state)
    return True

# ---------------------------------------------------------
#  Input
# ---------------------------------------------------------

def set_input(device, code):
    import app.core.db as db
    db.update_status_field(device["id"], "input", code)
    return True

# ---------------------------------------------------------
#  Volume
# ---------------------------------------------------------

def volume_change(device, delta):
    import app.core.db as db
    status = db.get_status(device["id"]) or {}
    current = status.get("volume") or 0
    new_value = max(0, min(100, current + delta))
    db.update_status_field(device["id"], "volume", new_value)
    return True

# ---------------------------------------------------------
#  Mute
# ---------------------------------------------------------

def set_mute(device, audio=None, video=None):
    import app.core.db as db
    if audio is not None:
        db.update_status_field(device["id"], "audio_mute", audio)
    if video is not None:
        db.update_status_field(device["id"], "video_mute", video)
    return True

