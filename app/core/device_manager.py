# device_manager.py

import app.core.db as db
from importlib import import_module
from app.core.autodetect import autodetect_capabilities


class DeviceManager:
    def __init__(self):
        print("[DeviceManager] Initializing, ensuring DB schema...")
        db.ensure_schema()
        self.device = db.get_device()

        if self.device:
            print(f"[DeviceManager] Loaded device id={self.device['id']} "
                  f"protocol={self.device.get('protocol')} "
                  f"host={self.device.get('host')} "
                  f"serial={self.device.get('serial_port')}")
        else:
            print("[DeviceManager] No device configured yet.")

    # ---------------------------------------------------------
    #  Capability helpers
    # ---------------------------------------------------------

    def _get_capabilities_dict(self):
        """
        DB lagrar capabilities som en lista med strängar.
        Vi konverterar till dict {cap: True}.
        """
        if not self.device:
            return {}

        caps = db.get_capabilities(self.device["id"])
        return {cap: True for cap in caps}

    def has_capability(self, cap):
        caps = self._get_capabilities_dict()
        return caps.get(cap, False)

    # ---------------------------------------------------------
    #  Driver loader
    # ---------------------------------------------------------

    def _get_driver_module(self):
        if not self.device:
            print("[DeviceManager] _get_driver_module: no device.")
            return None

        protocol = self.device.get("protocol")
        if not protocol:
            print("[DeviceManager] _get_driver_module: device has no protocol.")
            return None

        module_name = f"app.drivers.{protocol}_driver"
        print(f"[DeviceManager] Loading driver module: {module_name}")

        try:
            return import_module(module_name)
        except Exception as e:
            print(f"[DeviceManager] ERROR loading driver: {e}")
            return None

    # ---------------------------------------------------------
    #  Discovery + Autodetect
    # ---------------------------------------------------------

    def discover(self):
        """
        Kör discovery via serial och/eller nätverk.
        Sparar:
          - status
          - inputs
          - manufacturer/model
        Kör sedan autodetect_capabilities() och sparar resultatet.

        Verbos så man ser vad som händer.
        """
        if not self.device:
            print("[DeviceManager] discover: No device configured.")
            return False

        print("\n[DeviceManager] =============== DISCOVERY START ===============")
        print(f"[DeviceManager] Device id={self.device['id']} protocol={self.device.get('protocol')}")

        driver = self._get_driver_module()
        if not driver:
            print("[DeviceManager] discover: No valid driver.")
            print("[DeviceManager] =============== DISCOVERY END (FAILED) ===============")
            return False

        device_id = self.device["id"]
        discovered = False

        # -----------------------------------------------------
        #  Helper: merge info from driver into DB
        # -----------------------------------------------------
        def merge_info(info, source):
            print(f"[DeviceManager] Merging info from {source} discovery...")

            # Status
            if "status" in info:
                print(f"[DeviceManager]   - Updating status")
                db.update_status(device_id, info["status"])
            else:
                print(f"[DeviceManager]   - No status in info")

            # Inputs
            if "inputs" in info:
                print(f"[DeviceManager]   - Saving {len(info['inputs'])} inputs")
                db.save_inputs(device_id, info["inputs"])
            else:
                print(f"[DeviceManager]   - No inputs in info")

            # Manufacturer / Model
            if "manufacturer" in info:
                print(f"[DeviceManager]   - Setting manufacturer={info['manufacturer']}")
                db.update_device_field(device_id, "manufacturer", info["manufacturer"])
            if "model" in info:
                print(f"[DeviceManager]   - Setting model={info['model']}")
                db.update_device_field(device_id, "model", info["model"])

        # -----------------------------------------------------
        #  Serial discovery
        # -----------------------------------------------------
        if self.device.get("serial_port"):
            print("[DeviceManager] Trying SERIAL discovery...")
            try:
                if hasattr(driver, "discover_serial"):
                    info = driver.discover_serial(self.device["serial_port"])
                    if info:
                        print("[DeviceManager] SERIAL discovery succeeded.")
                        merge_info(info, "serial")
                        discovered = True
                    else:
                        print("[DeviceManager] SERIAL discovery returned no info.")
                else:
                    print("[DeviceManager] Driver has no discover_serial().")
            except Exception as e:
                print(f"[DeviceManager] SERIAL discovery failed: {e}")

        # -----------------------------------------------------
        #  Network discovery
        # -----------------------------------------------------
        if self.device.get("host"):
            print("[DeviceManager] Trying NETWORK discovery...")
            try:
                if hasattr(driver, "discover_net"):
                    info = driver.discover_net(self.device["host"], self.device.get("port"))
                    if info:
                        print("[DeviceManager] NETWORK discovery succeeded.")
                        merge_info(info, "network")
                        discovered = True
                    else:
                        print("[DeviceManager] NETWORK discovery returned no info.")
                else:
                    print("[DeviceManager] Driver has no discover_net().")
            except Exception as e:
                print(f"[DeviceManager] NETWORK discovery failed: {e}")

        if not discovered:
            print("[DeviceManager] No discovery method succeeded.")
            print("[DeviceManager] =============== DISCOVERY END (FAILED) ===============")
            return False

        # -----------------------------------------------------
        #  Autodetect capabilities
        # -----------------------------------------------------
        print("[DeviceManager] Starting capability autodetection...")
        try:
            caps = autodetect_capabilities(self.device)

            print("[DeviceManager] Autodetect finished. Capabilities:")
            for k, v in caps.items():
                print(f"    - {k}: {v}")

            print("[DeviceManager] Saving capabilities to DB...")
            db.save_capabilities(device_id, [k for k, v in caps.items() if v])
            print("[DeviceManager] Capabilities saved.")

        except Exception as e:
            print(f"[DeviceManager] Autodetect FAILED: {e}")
            print("[DeviceManager] =============== DISCOVERY END (PARTIAL) ===============")
            return False

        print("[DeviceManager] =============== DISCOVERY END (OK) ===============\n")
        return True

    # ---------------------------------------------------------
    #  Status
    # ---------------------------------------------------------

    def get_status(self):
        if not self.device:
            print("[DeviceManager] get_status: No device configured.")
            return None

        status = db.get_status(self.device["id"])
        if status is None:
            print("[DeviceManager] get_status: No status in DB. Run discover().")
        return status

    # ---------------------------------------------------------
    #  Commands
    # ---------------------------------------------------------

    def set_power(self, state):
        if not self.has_capability("power"):
            print("[DeviceManager] set_power: Device does not support power.")
            return False

        driver = self._get_driver_module()
        if not driver:
            print("[DeviceManager] set_power: No driver loaded.")
            return False

        print(f"[DeviceManager] set_power: Setting power={state}...")
        return driver.set_power(self.device, state)

    def set_input(self, code):
        if not self.has_capability("input"):
            print("[DeviceManager] set_input: Device does not support input switching.")
            return False

        driver = self._get_driver_module()
        if not driver:
            print("[DeviceManager] set_input: No driver loaded.")
            return False

        print(f"[DeviceManager] set_input: Switching to {code}...")
        return driver.set_input(self.device, code)

    def volume_change(self, delta):
        if not self.has_capability("volume"):
            print("[DeviceManager] volume_change: Device does not support volume.")
            return False

        driver = self._get_driver_module()
        if not driver:
            print("[DeviceManager] volume_change: No driver loaded.")
            return False

        print(f"[DeviceManager] volume_change: delta={delta}...")
        return driver.volume_change(self.device, delta)

    def set_mute(self, audio=None, video=None):
        caps = self._get_capabilities_dict()
        if not (caps.get("mute_audio") or caps.get("mute_video")):
            print("[DeviceManager] set_mute: Device does not support mute.")
            return False

        driver = self._get_driver_module()
        if not driver:
            print("[DeviceManager] set_mute: No driver loaded.")
            return False

        print(f"[DeviceManager] set_mute: audio={audio} video={video}...")
        return driver.set_mute(self.device, audio=audio, video=video)
