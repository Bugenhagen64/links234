# pjlink_net_driver.py
#
# Full PJLink Class 1 driver
# Stöd för:
# - INF1 (manufacturer)
# - INF2 (model)
# - POWR (power)
# - INPT (input)
# - AVMT (mute)
# - INST (input list)
# - ERST (error status)
# - LAMP (lamp hours)
#
# Discovery returnerar ett info-dict som DeviceManager kan spara direkt.

import socket
import re


# ---------------------------------------------------------
#  Low-level PJLink communication
# ---------------------------------------------------------

def _send(host, port, command, timeout=2):
    """
    Skickar ett PJLink-kommando och returnerar svaret som sträng.
    Hanterar Class 1 (ingen auth).
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))

        # Läs initial greeting
        greeting = s.recv(1024).decode().strip()

        # Class 1: ska börja med PJLINK 0
        if not greeting.startswith("PJLINK 0"):
            return None

        # Skicka kommandot
        s.send((command + "\r").encode())

        # Läs svar
        resp = s.recv(1024).decode().strip()
        s.close()

        # Format: "%1POWR=OK" eller "%1POWR=ERR3"
        if "=" in resp:
            return resp.split("=", 1)[1].strip()

        return None

    except Exception:
        return None


# ---------------------------------------------------------
#  Discovery helpers
# ---------------------------------------------------------

def _get_manufacturer(host, port):
    return _send(host, port, "%1INF1 ?")


def _get_model(host, port):
    return _send(host, port, "%1INF2 ?")


def _get_power(host, port):
    resp = _send(host, port, "%1POWR ?")
    return {
        "0": "off",
        "1": "on",
        "2": "cooling",
        "3": "warming"
    }.get(resp, "unknown")


def _get_input(host, port):
    resp = _send(host, port, "%1INPT ?")
    return resp  # ex: "31"


def _get_mute(host, port):
    resp = _send(host, port, "%1AVMT ?")
    if not resp:
        return {"audio_mute": False, "video_mute": False}

    # Format: "11" = audio mute ON, video mute ON
    audio = resp[0] == "1"
    video = resp[1] == "1"
    return {"audio_mute": audio, "video_mute": video}


def _get_inputs(host, port):
    resp = _send(host, port, "%1INST ?")
    if not resp:
        return []

    # Format: "11 21 31 32"
    codes = resp.split()
    result = []
    for code in codes:
        # Minimal mapping
        name = {
            "11": "RGB 1",
            "12": "RGB 2",
            "21": "Video",
            "22": "S-Video",
            "31": "HDMI 1",
            "32": "HDMI 2",
            "33": "HDMI 3",
        }.get(code, f"Input {code}")

        result.append({"name": name, "code": code})

    return result


def _get_lamps(host, port):
    resp = _send(host, port, "%1LAMP ?")
    if not resp:
        return []

    # Format: "1234 1 0 0" (hours1 on1 hours2 on2 ...)
    parts = resp.split()
    lamps = []

    # Varje lampa består av två värden
    for i in range(0, len(parts), 2):
        try:
            hours = int(parts[i])
            on = parts[i + 1] == "1"
            lamps.append({"hours": hours, "on": on})
        except Exception:
            pass

    return lamps


def _get_errors(host, port):
    resp = _send(host, port, "%1ERST ?")
    if not resp or len(resp) < 6:
        return {}

    return {
        "fan": resp[0],
        "lamp": resp[1],
        "temperature": resp[2],
        "cover": resp[3],
        "filter": resp[4],
        "other": resp[5],
    }


# ---------------------------------------------------------
#  Discovery API
# ---------------------------------------------------------

def discover_net(host, port):
    """
    Returnerar ett info-dict som DeviceManager sparar i DB.
    """
    info = {}

    # Manufacturer / Model
    info["manufacturer"] = _get_manufacturer(host, port)
    info["model"] = _get_model(host, port)

    # Status
    status = {}
    status["power"] = _get_power(host, port)
    status["input"] = _get_input(host, port)

    mute = _get_mute(host, port)
    status["audio_mute"] = mute["audio_mute"]
    status["video_mute"] = mute["video_mute"]

    # Lampor (kan vara tom lista för skärmar)
    lamps = _get_lamps(host, port)
    if lamps:
        status["lamps"] = lamps

    # Felstatus
    errors = _get_errors(host, port)
    if errors:
        status["errors"] = errors

    info["status"] = status

    # Inputs
    info["inputs"] = _get_inputs(host, port)

    # Capabilities
    caps = ["power", "input", "mute"]
    if lamps:
        caps.append("lamp")
    info["capabilities"] = caps

    return info


def discover_serial(port):
    # PJLink är nätverksbaserat – ingen serial
    return None


# ---------------------------------------------------------
#  Commands
# ---------------------------------------------------------

def set_power(device, state):
    host = device["host"]
    port = device["port"]
    cmd = "1" if state == "on" else "0"
    resp = _send(host, port, f"%1POWR {cmd}")
    return resp == "OK"


def set_input(device, code):
    host = device["host"]
    port = device["port"]
    resp = _send(host, port, f"%1INPT {code}")
    return resp == "OK"


def volume_change(device, delta):
    # PJLink Class 1 har inget volymkommando
    return False


def set_mute(device, audio=None, video=None):
    host = device["host"]
    port = device["port"]

    # Hämta nuvarande mute-status
    mute = _get_mute(host, port)
    audio_mute = mute["audio_mute"]
    video_mute = mute["video_mute"]

    if audio is not None:
        audio_mute = audio
    if video is not None:
        video_mute = video

    cmd = f"{int(audio_mute)}{int(video_mute)}"
    resp = _send(host, port, f"%1AVMT {cmd}")
    return resp == "OK"

