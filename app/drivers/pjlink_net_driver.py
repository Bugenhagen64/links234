# pjlink_driver.py

import re
from app.transport.transport_net import send_tcp


PJLINK_PORT = 4352


# ---------------------------------------------------------
#  Helpers
# ---------------------------------------------------------

def _parse_pjlink_response(resp):
    """
    Tar bort PJLINK-header och returnerar ren payload.
    Exempel:
        "PJLINK 0OK" → "OK"
        "PJLINK 0ER401" → "ER401"
    """
    if resp.startswith("PJLINK"):
        return resp.split(" ", 1)[1].strip()
    return resp.strip()


# ---------------------------------------------------------
#  Discovery
# ---------------------------------------------------------

def discover(host, password=None, timeout=5):
    """
    Testar om projektorn svarar på PJLink.
    Returnerar:
        {
            "brand": "...",
            "model": "...",
            "inputs": [...],
            "capabilities": {...}
        }
    """
    # Fråga om modellnamn
    resp = send_tcp(host, PJLINK_PORT, "%1INF1 ?", timeout)
    payload = _parse_pjlink_response(resp)

    if payload.startswith("ER"):
        raise Exception(f"PJLink error: {payload}")

    model = payload

    # Inputs
    resp = send_tcp(host, PJLINK_PORT, "%1INPT ?", timeout)
    payload = _parse_pjlink_response(resp)

    inputs = []
    if payload and payload[0].isdigit():
        for code in payload.split():
            inputs.append({
                "code": code,
                "type": "unknown",
                "name": f"Input {code}"
            })

    # Capabilities (PJLink Class 1)
    capabilities = {
        "supports_volume": 0,
        "supports_mute_audio": 1,
        "supports_mute_video": 1,
        "supports_class2": 0,
        "supports_input_query": 1
    }

    return {
        "brand": "Unknown (PJLink)",
        "model": model,
        "inputs": inputs,
        "capabilities": capabilities
    }


# ---------------------------------------------------------
#  Status
# ---------------------------------------------------------

def get_status(device):
    host = device["host"]
    timeout = device["timeout"]

    # Power
    resp = send_tcp(host, PJLINK_PORT, "%1POWR ?", timeout)
    power = _parse_pjlink_response(resp)

    power_map = {
        "0": "off",
        "1": "on",
        "2": "cooling",
        "3": "warming"
    }
    power_state = power_map.get(power, "unknown")

    # Input
    resp = send_tcp(host, PJLINK_PORT, "%1INPT ?", timeout)
    input_code = _parse_pjlink_response(resp)

    return {
        "power": power_state,
        "input": input_code,
        "volume": None,
        "mute_audio": None,
        "mute_video": None,
        "last_error": None
    }


# ---------------------------------------------------------
#  Commands
# ---------------------------------------------------------

def set_power(device, state):
    host = device["host"]
    timeout = device["timeout"]

    cmd = "%1POWR 1" if state == "on" else "%1POWR 0"
    resp = send_tcp(host, PJLINK_PORT, cmd, timeout)
    payload = _parse_pjlink_response(resp)

    if payload != "OK":
        raise Exception(f"PJLink power error: {payload}")


def set_input(device, code):
    host = device["host"]
    timeout = device["timeout"]

    resp = send_tcp(host, PJLINK_PORT, f"%1INPT {code}", timeout)
    payload = _parse_pjlink_response(resp)

    if payload != "OK":
        raise Exception(f"PJLink input error: {payload}")


def volume_change(device, delta):
    raise NotImplementedError("PJLink Class 1 har ingen volymkontroll")


def set_mute(device, audio=None, video=None):
    host = device["host"]
    timeout = device["timeout"]

    if audio is not None:
        cmd = "%1AVMT 1" if audio else "%1AVMT 0"
        resp = send_tcp(host, PJLINK_PORT, cmd, timeout)
        if _parse_pjlink_response(resp) != "OK":
            raise Exception("PJLink audio mute error")

    if video is not None:
        cmd = "%1AVMT 3" if video else "%1AVMT 2"
        resp = send_tcp(host, PJLINK_PORT, cmd, timeout)
        if _parse_pjlink_response(resp) != "OK":
            raise Exception("PJLink video mute error")
