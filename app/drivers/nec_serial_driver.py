# nec_serial_driver.py

from app.transport.transport_serial import send_serial


# ---------------------------------------------------------
#  Helpers
# ---------------------------------------------------------

def _clean(resp):
    """Ta bort kontrolltecken och whitespace."""
    if not resp:
        return ""
    return resp.strip().replace("\r", "").replace("\n", "")


# ---------------------------------------------------------
#  Discovery
# ---------------------------------------------------------

def discover(serial_port, timeout=5):
    """
    NEC discovery via RS232.
    Returnerar:
        {
            "brand": "NEC",
            "model": "...",
            "inputs": [...],
            "capabilities": {...}
        }
    """

    # Modellnamn
    resp = send_serial(serial_port, "00VR?", timeout)
    model = _clean(resp)

    if not model:
        raise Exception("NEC: ingen respons på 00VR?")

    # Inputs
    resp = send_serial(serial_port, "00INPT?", timeout)
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
    port = device["port_serial"]
    timeout = device["timeout"]

    # Power
    resp = send_serial(port, "00PWR?", timeout)
    power_raw = _clean(resp)

    power_map = {
        "00": "off",
        "01": "on",
        "02": "cooling",
        "03": "warming"
    }
    power = power_map.get(power_raw, "unknown")

    # Input
    resp = send_serial(port, "00INPT?", timeout)
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
    port = device["port_serial"]
    timeout = device["timeout"]

    cmd = "00PWR1" if state == "on" else "00PWR0"
    resp = send_serial(port, cmd, timeout)

    if not _clean(resp).endswith("OK"):
        raise Exception("NEC power error")


def set_input(device, code):
    port = device["port_serial"]
    timeout = device["timeout"]

    resp = send_serial(port, f"00INPT{code}", timeout)
    if not _clean(resp).endswith("OK"):
        raise Exception("NEC input error")


def volume_change(device, delta):
    port = device["port_serial"]
    timeout = device["timeout"]

    cmd = "00VOL+" if delta > 0 else "00VOL-"
    resp = send_serial(port, cmd, timeout)

    if not _clean(resp).endswith("OK"):
        raise Exception("NEC volume error")


def set_mute(device, audio=None, video=None):
    port = device["port_serial"]
    timeout = device["timeout"]

    if audio is not None:
        cmd = "00AMT1" if audio else "00AMT0"
        resp = send_serial(port, cmd, timeout)
        if not _clean(resp).endswith("OK"):
            raise Exception("NEC audio mute error")

    if video is not None:
        cmd = "00VMT1" if video else "00VMT0"
        resp = send_serial(port, cmd, timeout)
        if not _clean(resp).endswith("OK"):
            raise Exception("NEC video mute error")

