# nec_net_driver.py

import time
from app.transport.transport_net import send_tcp


NEC_PORT = 7142


# ---------------------------------------------------------
#  Helpers
# ---------------------------------------------------------

def _clean(resp):
    """Ta bort kontrolltecken och whitespace."""
    if not resp:
        return ""
    return resp.strip().replace("\r", "").replace("\n", "")


def _send(host, payload, timeout):
    """
    NEC över TCP kräver CR på slutet.
    """
    cmd = payload + "\r"
    resp = send_tcp(host, NEC_PORT, cmd, timeout)
    return _clean(resp)


# ---------------------------------------------------------
#  Discovery
# ---------------------------------------------------------

def discover(host, timeout=5):
    """
    NEC discovery via TCP port 7142.
    Returnerar:
        {
            "brand": "NEC",
            "model": "...",
            "inputs": [...],
            "capabilities": {...}
        }
    """

    # Modellnamn
    resp = _send(host, "00VR?", timeout)
    model = _clean(resp)

    if not model:
        raise Exception("NEC NET: ingen respons på 00VR?")

    # Inputs
    resp = _send(host, "00INPT?", timeout)
    payload = _clean(resp)

    inputs = []
    if payload:
        for code in payload.split(","):
            inputs.append({
                "code": code,
                "type": "unknown",
                "name": f"Input {code}"
            })

    capabilities = {
        "supports_volume": 1,
        "supports_mute_audio": 1,
        "supports_mute_video": 1,
        "supports_class2": 0,
        "supports_input_query": 1
    }

    return {
        "brand": "NEC",
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
    resp = _send(host, "00PWR?", timeout)
    power_raw = _clean(resp)

    power_map = {
        "00": "off",
        "01": "on",
        "02": "cooling",
        "03": "warming"
    }
    power = power_map.get(power_raw, "unknown")

    # Input
    resp = _send(host, "00INPT?", timeout)
    input_code = _clean(resp)

    return {
        "power": power,
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

    cmd = "00PWR1" if state == "on" else "00PWR0"
    resp = _send(host, cmd, timeout)

    if not resp.endswith("OK"):
        raise Exception(f"NEC NET power error: {resp}")


def set_input(device, code):
    host = device["host"]
    timeout = device["timeout"]

    resp = _send(host, f"00INPT{code}", timeout)
    if not resp.endswith("OK"):
        raise Exception(f"NEC NET input error: {resp}")


def volume_change(device, delta):
    host = device["host"]
    timeout = device["timeout"]

    cmd = "00VOL+" if delta > 0 else "00VOL-"
    resp = _send(host, cmd, timeout)

    if not resp.endswith("OK"):
        raise Exception(f"NEC NET volume error: {resp}")


def set_mute(device, audio=None, video=None):
    host = device["host"]
    timeout = device["timeout"]

    if audio is not None:
        cmd = "00AMT1" if audio else "00AMT0"
        resp = _send(host, cmd, timeout)
        if not resp.endswith("OK"):
            raise Exception(f"NEC NET audio mute error: {resp}")

    if video is not None:
        cmd = "00VMT1" if video else "00VMT0"
        resp = _send(host, cmd, timeout)
        if not resp.endswith("OK"):
            raise Exception(f"NEC NET video mute error: {resp}")

