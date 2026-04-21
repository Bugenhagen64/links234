# autodetect_capabilities.py

import importlib
import time


def autodetect_capabilities(device):
    """
    Autodetekterar capabilities för en device baserat på dess driver.
    Returnerar en dict {capability: True/False}.

    Verbos loggning så man ser exakt vad som händer.
    """

    print("[Autodetect] Starting capability autodetection...")
    protocol = device.get("protocol")

    if not protocol:
        print("[Autodetect] ERROR: Device has no protocol.")
        return {}

    module_name = f"app.drivers.{protocol}_driver"
    print(f"[Autodetect] Loading driver module: {module_name}")

    try:
        driver = importlib.import_module(module_name)
    except Exception as e:
        print(f"[Autodetect] ERROR loading driver: {e}")
        return {}

    # Fake-driver eller drivers som inte vill autodetekteras
    if not getattr(driver, "supports_autodetect", False):
        print("[Autodetect] Driver does not support autodetect. Using base_capabilities.")
        return driver.base_capabilities.copy()

    base = driver.base_capabilities.copy()
    result = {}

    print("[Autodetect] Base capabilities:")
    for cap, supported in base.items():
        print(f"    - {cap}: {supported}")

    print("[Autodetect] Beginning probing...\n")

    for cap, supported in base.items():
        print(f"[Autodetect] Probing capability: {cap}")

        if not supported:
            print(f"[Autodetect]   - Protocol does NOT support {cap}. Marking False.\n")
            result[cap] = False
            continue

        # Finns en probe_<cap>() i drivern?
        probe_fn = getattr(driver, f"probe_{cap}", None)
        if probe_fn:
            print(f"[Autodetect]   - Using driver-specific probe_{cap}()")
            try:
                ok = bool(probe_fn(device))
                print(f"[Autodetect]   - probe_{cap}() returned {ok}\n")
                result[cap] = ok
            except Exception as e:
                print(f"[Autodetect]   - probe_{cap}() FAILED: {e}")
                result[cap] = False
            continue

        # Ingen probe-funktion → försök generisk probing
        print(f"[Autodetect]   - No probe_{cap}() found. Using generic probing.")
        ok = _generic_probe(cap, device, driver)
        print(f"[Autodetect]   - Generic probe result: {ok}\n")
        result[cap] = ok

    print("[Autodetect] All probing complete.\n")
    return result


# ---------------------------------------------------------
#  Generic probing
# ---------------------------------------------------------

def _generic_probe(cap, device, driver):
    """
    Generisk probing för capabilities där drivern inte har en probe_<cap>().
    Detta är frivilligt och kan byggas ut.
    """

    host = device.get("host")
    port = device.get("port")
    timeout = device.get("timeout", 5)

    module_name = driver.__name__

    # -----------------------------------------------------
    #  PJLink generic probing
    # -----------------------------------------------------
    if module_name.endswith("pjlink_net_driver"):
        from app.drivers.pjlink_net_driver import _send

        tests = {
            "power": "%1POWR ?",
            "input": "%1INPT ?",
            "mute_audio": "%1AVMT ?",
            "mute_video": "%1AVMT ?",
            "lamp_hours": "%1LAMP ?",
            "errors": "%1ERST ?",
            "class2": "%2POWR ?"
        }

        cmd = tests.get(cap)
        if not cmd:
            print(f"[Autodetect]   - No generic PJLink test for {cap}. Marking False.")
            return False

        print(f"[Autodetect]   - Sending PJLink command: {cmd}")
        resp = _send(host, port, cmd)
        print(f"[Autodetect]   - Response: {resp}")

        if resp in (None, "ERR2"):
            return False
        return True

    # -----------------------------------------------------
    #  NEC NET generic probing
    # -----------------------------------------------------
    if module_name.endswith("nec_net_driver"):
        from app.drivers.nec_net_driver import _send

        tests = {
            "power": "00PWR?",
            "input": "00INPT?",
            "volume": "00VOL?",
            "mute_audio": "00AMT?",
            "mute_video": "00VMT?",
            "lamp_hours": "00LAMP?",
            "errors": "00ERR?"
        }

        cmd = tests.get(cap)
        if not cmd:
            print(f"[Autodetect]   - No generic NEC-NET test for {cap}. Marking False.")
            return False

        print(f"[Autodetect]   - Sending NEC-NET command: {cmd}")
        resp = _send(host, cmd, timeout)
        print(f"[Autodetect]   - Response: {resp}")

        if resp in ("", None):
            return False
        return True

    # -----------------------------------------------------
    #  NEC SERIAL generic probing
    # -----------------------------------------------------
    if module_name.endswith("nec_serial_driver"):
        from app.drivers.nec_serial_driver import send_serial

        tests = {
            "power": "00PWR?",
            "input": "00INPT?",
            "volume": "00VOL?",
            "mute_audio": "00AMT?",
            "mute_video": "00VMT?",
            "lamp_hours": "00LAMP?",
            "errors": "00ERR?"
        }

        cmd = tests.get(cap)
        if not cmd:
            print(f"[Autodetect]   - No generic NEC-SERIAL test for {cap}. Marking False.")
            return False

        print(f"[Autodetect]   - Sending NEC-SERIAL command: {cmd}")
        resp = send_serial(device["port_serial"], cmd, timeout)
        print(f"[Autodetect]   - Response: {resp}")

        if resp in ("", None):
            return False
        return True

    # -----------------------------------------------------
    #  Unknown driver type
    # -----------------------------------------------------
    print(f"[Autodetect]   - No generic probing available for driver {module_name}.")
    return False

