# pjlink_net_driver.py
#
# PJLink Class 1/2 Network Control
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

# Protokoll-nivåns möjligheter (vad PJLink *kan* i teorin)
base_capabilities = {
    "power": True,
    "input": True,
    "volume": False,       # PJLink har ingen volymkontroll
    "mute_audio": True,
    "mute_video": True,
    "freeze": False,
    "shutter": False,
    "lamp_hours": True,
    "errors": True,
    "lens_shift": False,
    "zoom": False,
    "focus": False,
    "class2": True         # Class 2-kommandon
}


# ---------------------------------------------------------
#  Low-level PJLink send
# ---------------------------------------------------------

def _send(host, port, cmd, timeout=5):
    """
    Skickar ett PJLink-kommando.
    Returnerar råtext eller None vid fel.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
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
    resp = _send(device["host"], device["port"], "%1POWR ?", device.get("timeout", 5))
    return resp not in (None, "ERR2")

def probe_input(device):
    resp = _send(device["host"], device["port"], "%1INPT ?", device.get("timeout", 5))
    return resp not in (None, "ERR2")

def probe_mute_audio(device):
    resp = _send(device["host"], device["port"], "%1AVMT ?", device.get("timeout", 5))
    return resp not in (None, "ERR2")

def probe_mute_video(device):
    resp = _send(device["host"], device["port"], "%1AVMT ?", device.get("timeout", 5))
    return resp not in (None, "ERR2")

def probe_lamp_hours(device):
    resp = _send(device["host"], device["port"], "%1LAMP ?", device.get("timeout", 5))
    return resp not in (None, "ERR2")

def probe_errors(device):
    resp = _send(device["host"], device["port"], "%1ERST ?", device.get("timeout", 5))
    return resp not in (None, "ERR2")

def probe_class2(device):
    resp = _send(device["host"], device["port"], "%2POWR ?", device.get("timeout", 5))
    return resp not in (None, "ERR2")


# ---------------------------------------------------------
#  Discovery
# ---------------------------------------------------------

def discover_net(host, port):
    """
    PJLink discovery via TCP.
    Returnerar:
        {
            "manufacturer": "...",
            "model": "...",
            "inputs": [...],
            "status": {...}
        }
    """

    timeout = 5

    # Modellnamn
    model = _send(host, port, "%1NAME ?", timeout)
    if not model:
        raise Exception("PJLink: ingen respons på %1NAME ?")

    # Manufacturer
    manufacturer = _send(host, port, "%1INF1 ?", timeout) or "Unknown"

    # Inputs
    inputs_raw = _send(host, port, "%1INST ?", timeout)
    inputs = []
    if inputs_raw and inputs_raw.startswith("INST="):
        try:
            payload = inputs_raw.split("=")[1]
            for entry in payload.split(";"):
                if not entry:
                    continue
                code, name = entry.split(",")
                inputs.append({"code": code, "name": name})
        except:
            pass

    # Status
    status = {}

    # Power
    power_raw = _send(host, port, "%1POWR ?", timeout)
    power_map = {
        "0": "off",
        "1": "on",
        "2": "cooling",
        "3": "warming"
    }
    if power_raw and power_raw.startswith("POWR="):
        status["power"] = power_map.get(power_raw.split("=")[1], "unknown")
    else:
        status["power"] = "unknown"

    # Input
    input_raw = _send(host, port, "%1INPT ?", timeout)
    if input_raw and input_raw.startswith("INPT="):
        status["input"] = input_raw.split("=")[1]
    else:
        status["input"] = None

    # Mute
    mute_raw = _send(host, port, "%1AVMT ?", timeout)
    if mute_raw and mute_raw.startswith("AVMT="):
        try:
            a, v = mute_raw.split("=")[1].split(",")
            status["audio_mute"] = (a == "1")
            status["video_mute"] = (v == "1")
        except:
            status["audio_mute"] = None
            status["video_mute"] = None
    else:
        status["audio_mute"] = None
        status["video_mute"] = None

    # Lamp hours
    lamp_raw = _send(host, port, "%1LAMP ?", timeout)
    lamps = []
    if lamp_raw and lamp_raw.startswith("LAMP="):
        try:
            parts = lamp_raw.split("=")[1].split(" ")
            for i in range(0, len(parts), 2):
                hours = int(parts[i])
                on = (parts[i+1] == "1")
                lamps.append({"hours": hours, "on": on})
        except:
            pass
    status["lamps"] = lamps

    # Errors
    err_raw = _send(host, port, "%1ERST ?", timeout)
    if err_raw and err_raw.startswith("ERST="):
        status["errors"] = {"raw": err_raw.split("=")[1]}
    else:
        status["errors"] = {}

    return {
        "manufacturer": manufacturer,
        "model": model,
        "inputs": inputs,
        "status": status
    }


# ---------------------------------------------------------
#  Status polling
# ---------------------------------------------------------

def get_status(device):
    host = device["host"]
    port = device["port"]
    timeout = device.get("timeout", 5)

    # Power
    power_raw = _send(host, port, "%1POWR ?", timeout)
    power_map = {
        "0": "off",
        "1": "on",
        "2": "cooling",
        "3": "warming"
    }
    if power_raw and power_raw.startswith("POWR="):
        power = power_map.get(power_raw.split("=")[1], "unknown")
    else:
        power = "unknown"

    # Input
    input_raw = _send(host, port, "%1INPT ?", timeout)
    if input_raw and input_raw.startswith("INPT="):
        input_code = input_raw.split("=")[1]
    else:
        input_code = None

    # Mute
    mute_raw = _send(host, port, "%1AVMT ?", timeout)
    audio_mute = None
    video_mute = None
    if mute_raw and mute_raw.startswith("AVMT="):
        try:
            a, v = mute_raw.split("=")[1].split(",")
            audio_mute = (a == "1")
            video_mute = (v == "1")
        except:
            pass

    return {
        "power": power,
        "input": input_code,
        "volume": None,
        "audio_mute": audio_mute,
        "video_mute": video_mute,
        "errors": None,
        "lamps": None
    }


# ---------------------------------------------------------
#  Commands
# ---------------------------------------------------------

def set_power(device, state):
    host = device["host"]
    port = device["port"]
    timeout = device.get("timeout", 5)

    cmd = "%1POWR 1" if state == "on" else "%1POWR 0"
    resp = _send(host, port, cmd, timeout)
    return bool(resp and resp.endswith("OK"))

def set_input(device, code):
    host = device["host"]
    port = device["port"]
    timeout = device.get("timeout", 5)

    resp = _send(host, port, f"%1INPT {code}", timeout)
    return bool(resp and resp.endswith("OK"))

def volume_change(device, delta):
    # PJLink har ingen volymkontroll
    return False

def set_mute(device, audio=None, video=None):
    host = device["host"]
    port = device["port"]
    timeout = device.get("timeout", 5)

    ok = True

    if audio is not None:
        cmd = "%1AVMT 1,0" if audio else "%1AVMT 0,0"
        resp = _send(host, port, cmd, timeout)
        ok = ok and bool(resp and resp.endswith("OK"))

    if video is not None:
        cmd = "%1AVMT 0,1" if video else "%1AVMT 0,0"
        resp = _send(host, port, cmd, timeout)
        ok = ok and bool(resp and resp.endswith("OK"))

    return ok
