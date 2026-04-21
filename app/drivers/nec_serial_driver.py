# nec_serial_driver.py
#
# NEC Serial Control Protocol (RS232)
# Städad version enligt nya arkitekturen:
# - Inga capabilities i discovery
# - base_capabilities + supports_autodetect
# - probe_xxx() för autodetect
# - konsekvent status-dict
# - renare kod

import serial
import time


# ---------------------------------------------------------
#  Driver metadata
# ---------------------------------------------------------

supports_autodetect = True

# Protokoll-nivåns möjligheter (vad NEC SERIAL *kan* i teorin)
base_capabilities = {
    "power": True,
    "input": True,
    "volume": True,
    "mute_audio": True,
    "mute_video": True,
    "freeze": False,
    "shutter": False,
    "lamp_hours": True,   # många NEC-modeller har 00LAMP?
    "errors": True,       # vissa har 00ERR?
    "lens_shift": False,
    "zoom": False,
    "focus": False,
    "class2": False
}


# ---------------------------------------------------------
#  Low-level serial send
# ---------------------------------------------------------

def send_serial(port, cmd, timeout=5):
    """
    Skickar ett NEC-kommandon via RS232.
    Returnerar råtext eller None vid fel.
    """
    try:
        with serial.Serial(port, baudrate=9600, timeout=timeout) as ser:
            ser.write((cmd + "\r").encode("ascii"))
            ser.flush()
            data = ser.readline().decode("ascii").strip()
            if not data:
                return None
            return data
    except Exception:
        return None


def _clean(resp):
    if not resp:
        return None
    return resp.strip()


# ---------------------------------------------------------
#  Probe functions (för autodetect)
# ---------------------------------------------------------

def probe_power(device):
    resp = send_serial(device["serial_port"], "00PWR?", device.get("timeout", 5))
    return _clean(resp) not in ("", None)

def probe_input(device):
    resp = send_serial(device["serial_port"], "00INPT?", device.get("timeout", 5))
    return _clean(resp) not in ("", None)

def probe_volume(device):
    resp = send_serial(device["serial_port"], "00VOL?", device.get("timeout", 5))
    return _clean(resp) not in ("", None)

def probe_mute_audio(device):
    resp = send_serial(device["serial_port"], "00AMT?", device.get("timeout", 5))
    return _clean(resp) not in ("", None)

def probe_mute_video(device):
    resp = send_serial(device["serial_port"], "00VMT?", device.get("timeout", 5))
    return _clean(resp) not in ("", None)

def probe_lamp_hours(device):
    resp = send_serial(device["serial_port"], "00LAMP?", device.get("timeout", 5))
    return _clean(resp) not in ("", None)

def probe_errors(device):
    resp = send_serial(device["serial_port"], "00ERR?", device.get("timeout", 5))
    return _clean(resp) not in ("", None)


# ---------------------------------------------------------
#  Discovery
# ---------------------------------------------------------

def discover_serial(port):
    """
    NEC discovery via RS232.
    Returnerar:
        {
            "manufacturer": "NEC",
            "model": "...",
            "inputs": [...],
            "status": {...}
        }
    """

    timeout = 5

    # Modellnamn
    model = send_serial(port, "00VR?", timeout)
    if not model:
        raise Exception("NEC SERIAL: ingen respons på 00VR?")

    # Inputs
    payload = send_serial(port, "00INPT?", timeout)
    inputs = []
    if payload:
        for code in payload.split(","):
            inputs.append({
                "code": code,
                "name": f"Input {code}",
                "type": "unknown"
            })

    # Status
    status = {}

    # Power
    power_raw = send_serial(port, "00PWR?", timeout)
    power_map = {
        "00": "off",
        "01": "on",
        "02": "cooling",
        "03": "warming"
    }
    status["power"] = power_map.get(power_raw, "unknown")

    # Input
    status["input"] = send_serial(port, "00INPT?", timeout)

    # Volume (okänd nivå)
    status["volume"] = None

    # Mute (okänd initial status)
    status["audio_mute"] = None
    status["video_mute"] = None

    # Lamp hours
    lamp_raw = send_serial(port, "00LAMP?", timeout)
    if lamp_raw and lamp_raw != "ERR":
        try:
            status["lamps"] = [{"hours": int(lamp_raw), "on": None}]
        except:
            status["lamps"] = []
    else:
        status["lamps"] = []

    # Errors
    err_raw = send_serial(port, "00ERR?", timeout)
    if err_raw and err_raw != "ERR":
        status["errors"] = {"raw": err_raw}
    else:
        status["errors"] = {}

    return {
        "manufacturer": "NEC",
        "model": model,
        "inputs": inputs,
        "status": status
    }


# ---------------------------------------------------------
#  Status polling
# ---------------------------------------------------------

def get_status(device):
    port = device["serial_port"]
    timeout = device.get("timeout", 5)

    # Power
    power_raw = send_serial(port, "00PWR?", timeout)
    power_map = {
        "00": "off",
        "01": "on",
        "02": "cooling",
        "03": "warming"
    }
    power = power_map.get(power_raw, "unknown")

    # Input
    input_code = send_serial(port, "00INPT?", timeout)

    return {
        "power": power,
        "input": input_code,
        "volume": None,
        "audio_mute": None,
        "video_mute": None,
        "errors": None,
        "lamps": None
    }


# ---------------------------------------------------------
#  Commands
# ---------------------------------------------------------

def set_power(device, state):
    port = device["serial_port"]
    timeout = device.get("timeout", 5)

    cmd = "00PWR1" if state == "on" else "00PWR0"
    resp = send_serial(port, cmd, timeout)
    return bool(resp and resp.endswith("OK"))

def set_input(device, code):
    port = device["serial_port"]
    timeout = device.get("timeout", 5)

    resp = send_serial(port, f"00INPT{code}", timeout)
    return bool(resp and resp.endswith("OK"))

def volume_change(device, delta):
    port = device["serial_port"]
    timeout = device.get("timeout", 5)

    cmd = "00VOL+" if delta > 0 else "00VOL-"
    resp = send_serial(port, cmd, timeout)
    return bool(resp and resp.endswith("OK"))

def set_mute(device, audio=None, video=None):
    port = device["serial_port"]
    timeout = device.get("timeout", 5)

    ok = True

    if audio is not None:
        cmd = "00AMT1" if audio else "00AMT0"
        resp = send_serial(port, cmd, timeout)
        ok = ok and bool(resp and resp.endswith("OK"))

    if video is not None:
        cmd = "00VMT1" if video else "00VMT0"
        resp = send_serial(port, cmd, timeout)
        ok = ok and bool(resp and resp.endswith("OK"))

    return ok
