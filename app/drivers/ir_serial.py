# ir_driver.py
#
# IR-driver för enheter som styrs via en USB-IR-blaster.
#
# Den här versionen fungerar fullt ut i systemet:
# - discovery fungerar (returnerar "unknown" status)
# - kommandon fungerar (skickar placeholders)
# - capabilities fungerar
# - DeviceManager kan använda den
#
# MEN: riktiga IR-koder saknas.
#
# När du vill styra en riktig projektor behöver du:
#   1) En liten DB-tabell för IR-koder (device_id, function, code)
#   2) CLI-stöd för att lägga in koder
#   3) Att ersätta placeholder-koderna nedan
#
# Den här drivern är alltså 100% klar för integration,
# men 0% klar för verklig IR-styrning (vilket är avsiktligt just nu).

from app.transport.transport_ir import send_ir

supports_autodetect = False

# IR kan bara skicka kommandon, aldrig läsa status.
base_capabilities = {
    "power": True,
    "input": True,
    "volume": True,
    "mute_audio": True,
    "mute_video": False,
    "freeze": False,
    "shutter": False,
    "lamp_hours": False,
    "errors": False,
    "lens_shift": False,
    "zoom": False,
    "focus": False,
    "class2": False
}

# ---------------------------------------------------------
#  Discovery
# ---------------------------------------------------------

def discover(device):
    """
    IR-enheter kan inte upptäckas automatiskt.
    Vi returnerar en generisk "unknown" device.
    """

    return {
        "manufacturer": "Unknown (IR)",
        "model": "IR-Controlled Device",
        "inputs": [],  # IR kan inte läsa inputs
        "status": {
            "power": "unknown",
            "input": "unknown",
            "volume": None,
            "audio_mute": None,
            "video_mute": None,
            "lamps": None,
            "errors": None
        }
    }

# ---------------------------------------------------------
#  Status
# ---------------------------------------------------------

def get_status(device):
    """
    IR kan inte läsa status.
    Vi returnerar alltid "unknown".
    """

    return {
        "power": "unknown",
        "input": "unknown",
        "volume": None,
        "audio_mute": None,
        "video_mute": None,
        "errors": None,
        "lamps": None
    }

# ---------------------------------------------------------
#  Kommandon
# ---------------------------------------------------------

# OBS: Dessa är placeholders.
# När du har riktiga IR-koder ska du ersätta dem.
# T.ex.:
#   code = db.get_ir_code(device["id"], "power_on")
#   send_ir(device["serial_port"], code)

def set_power(device, state):
    port = device.get("serial_port")
    if not port:
        return False

    # TODO: ersätt med riktig IR-kod
    code = "IR_POWER_ON" if state == "on" else "IR_POWER_OFF"

    return send_ir(port, code)

def set_input(device, code):
    port = device.get("serial_port")
    if not port:
        return False

    # TODO: ersätt med riktig IR-kod
    ir_code = f"IR_INPUT_{code}"

    return send_ir(port, ir_code)

def volume_change(device, delta):
    port = device.get("serial_port")
    if not port:
        return False

    # TODO: ersätt med riktiga IR-koder
    ir_code = "IR_VOL_UP" if delta > 0 else "IR_VOL_DOWN"

    return send_ir(port, ir_code)

def set_mute(device, audio=None, video=None):
    port = device.get("serial_port")
    if not port:
        return False

    ok = True

    if audio is not None:
        # TODO: ersätt med riktig IR-kod
        ir_code = "IR_MUTE_ON" if audio else "IR_MUTE_OFF"
        ok = ok and send_ir(port, ir_code)

    # IR-video-mute är ovanligt → stöds ej
    return ok

