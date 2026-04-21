# nec_net_driver.py
#
# NEC Network Control Protocol (TCP)
# Städad version enligt nya arkitekturen:
# - Inga capabilities i discovery
# - base_capabilities + supports_autodetect
# - probe_xxx() för autodetect
# - konsekvent status-dict
# - renare kod

import socket
import time


# ---------------------------------------------------------
#  Driver metadata
# ---------------------------------------------------------

supports_autodetect = True

# Protokoll-nivåns möjligheter (vad NEC NET *kan* i teorin)
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
#  Low-level TCP send
# ---------------------------------------------------------

def _send(host, cmd, timeout=5):
    """
    Skickar ett NEC-kommandon via TCP.
    Returnerar råtext eller None vid fel.
    """
    try:
        with socket.create_connection((host, 7142), timeout=timeout) as s:
            s.sendall((cmd + "\r").encode("ascii"))
            s.settimeout(timeout)
            data = s.recv(1024)
            if not data:
                return None
            return data.decode("ascii").strip()
    except Exception:
        return None


# ---------------------------------------------------------
#  Probe functions (för autodetect)
# ---------------------------------------------------------

def probe_power(device):
    resp = _send(device["host"], "00PWR?", device.get("timeout", 5))
    return resp not in ("", None)

def probe_input(device):
    resp = _send(device["host"], "00INPT?", device.get("timeout", 5))
    return resp not in ("", None)

def probe_volume(device):
    resp = _send(device["host"], "00VOL?", device.get("timeout", 5))
    return resp not in ("", None)

def probe_mute_audio(device):
    resp = _send(device["host"], "00AMT?", device.get("timeout", 5))
    return resp not in ("", None)

def probe_mute_video(device):
    resp = _send(device["host"], "00VMT?", device.get("timeout", 5))
    return resp not in ("", None)

def probe_lamp_hours(device):
    resp = _send(device["host"], "00LAMP?", device.get("timeout", 5))
    return resp not in ("", None)

def probe_errors(device):
    resp = _send(device["host"], "00ERR?", device.get("timeout", 5))
    return resp not in ("", None)


# ---------------------------------------------------------
#  Discovery
# ---------------------------------------------------------

def discover_net(host, port=None):
    """
    NEC discovery via TCP.
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
    model = _send(host, "00VR?", timeout)
    if not model:
        raise Exception("NEC NET: ingen respons på 00VR?")

    # Inputs
    payload = _send(host, "00INPT?", timeout)
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
    power_raw = _send(host, "00PWR?", timeout)
    power_map = {
        "00": "off",
        "01": "on",
        "02": "cooling",
        "03": "warming"
    }
    status["power"] = power_map.get(power_raw, "unknown")

    # Input
    status["input"] = _send(host, "00INPT?", timeout)

    # Volume (okänd nivå)
    status["volume"] = None

    # Mute (okänd initial status)
    status["audio_mute"] = None
    status["video_mute"] = None

    # Lamp hours (om modellen stöder det)
    lamp_raw = _send(host, "00LAMP?", timeout)
    if lamp_raw and lamp_raw != "ERR":
        try:
            status["lamps"] = [{"hours": int(lamp_raw), "on": None}]
        except:
            status["lamps"] = []
    else:
        status["lamps"] = []

    # Errors (om modellen stöder det)
    err_raw = _send(host, "00ERR?", timeout)
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
    host = device["host"]
    timeout = device.get("timeout", 5)

    # Power
    power_raw = _send(host, "00PWR?", timeout)
    power_map = {
        "00": "off",
        "01": "on",
        "02": "cooling",
        "03": "warming"
    }
    power = power_map.get(power_raw, "unknown")

    # Input
    input_code = _send(host, "00INPT?", timeout)

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
    host = device["host"]
    timeout = device.get("timeout", 5)

    cmd = "00PWR1" if state == "on" else "00PWR0"
    resp = _send(host, cmd, timeout)
    return bool(resp and resp.endswith("OK"))

def set_input(device, code):
    host = device["host"]
    timeout = device.get("timeout", 5)

    resp = _send(host, f"00INPT{code}", timeout)
    return bool(resp and resp.endswith("OK"))

def volume_change(device, delta):
    host = device["host"]
    timeout = device.get("timeout", 5)

    cmd = "00VOL+" if delta > 0 else "00VOL-"
    resp = _send(host, cmd, timeout)
    return bool(resp and resp.endswith("OK"))

def set_mute(device, audio=None, video=None):
    host = device["host"]
    timeout = device.get("timeout", 5)

    ok = True

    if audio is not None:
        cmd = "00AMT1" if audio else "00AMT0"
        resp = _send(host, cmd, timeout)
        ok = ok and bool(resp and resp.endswith("OK"))

    if video is not None:
        cmd = "00VMT1" if video else "00VMT0"
        resp = _send(host, cmd, timeout)
        ok = ok and bool(resp and resp.endswith("OK"))

    return ok
