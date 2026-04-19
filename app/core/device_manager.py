# device_manager.py

import app.core.db as db
from importlib import import_module


class DeviceManager:
    def __init__(self):
        db.ensure_schema()
        self.device = db.get_device()

    # ---------------------------------------------------------
    #  Capability helper
    # ---------------------------------------------------------

    def has_capability(self, cap):
        if not self.device:
            return False
        caps = db.get_capabilities(self.device["id"])
        return cap in caps

    # ---------------------------------------------------------
    #  Driver loader
    # ---------------------------------------------------------

    def _get_driver_module(self):
        if not self.device:
            return None

        protocol = self.device.get("protocol")
        if not protocol:
            return None

        try:
            return import_module(f"app.drivers.{protocol}_driver")
        except ModuleNotFoundError:
            print(f"Driver not found for protocol: {protocol}")
            return None

    # ---------------------------------------------------------
    #  Discovery
    # ---------------------------------------------------------

    def discover(self):
        if not self.device:
            print("No device configured. Run setup first.")
            return False

        print("Starting discovery...")

        driver = self._get_driver_module()
        if not driver:
            print("No valid driver available.")
            return False

        device_id = self.device["id"]

        # -----------------------------------------------------
        #  Helper: merge info from driver into DB
        # -----------------------------------------------------
        def merge_status(info):
            # 1. Spara statusfält
            if "status" in info:
                db.update_status(device_id, info["status"])

            # 2. Spara capabilities
            if "capabilities" in info:
                db.save_capabilities(device_id, info["capabilities"])

            # 3. Spara inputs
            if "inputs" in info:
                db.save_inputs(device_id, info["inputs"])

            # 4. Spara manufacturer/model
            if "manufacturer" in info:
                db.update_device_field(device_id, "manufacturer", info["manufacturer"])

            if "model" in info:
                db.update_device_field(device_id, "model", info["model"])

        # -----------------------------------------------------
        #  Serial discovery
        # -----------------------------------------------------
        if self.device.get("serial_port"):
            try:
                info = driver.discover_serial(self.device["serial_port"])
                if info:
                    merge_status(info)
                    return True
            except Exception as e:
                print("Serial discovery failed:", e)

        # -----------------------------------------------------
        #  Network discovery
        # -----------------------------------------------------
        if self.device.get("host"):
            try:
                info = driver.discover_net(self.device["host"], self.device["port"])
                if info:
                    merge_status(info)
                    return True
            except Exception as e:
                print("Network discovery failed:", e)

        print("Discovery failed.")
        return False

    # ---------------------------------------------------------
    #  Status
    # ---------------------------------------------------------

    def get_status(self):
        if not self.device:
            print("No device configured. Run setup first.")
            return None

        return db.get_status(self.device["id"])

    # ---------------------------------------------------------
    #  Commands (stateless)
    # ---------------------------------------------------------

    def set_power(self, state):
        if not self.has_capability("power"):
            print("Device does not support power control.")
            return False

        driver = self._get_driver_module()
        if not driver:
            print("No device configured.")
            return False

        return driver.set_power(self.device, state)

    def set_input(self, code):
        if not self.has_capability("input"):
            print("Device does not support input switching.")
            return False

        driver = self._get_driver_module()
        if not driver:
            print("No device configured.")
            return False

        return driver.set_input(self.device, code)

    def volume_change(self, delta):
        if not self.has_capability("volume"):
            print("Device does not support volume control.")
            return False

        driver = self._get_driver_module()
        if not driver:
            print("No device configured.")
            return False

        return driver.volume_change(self.device, delta)

    def set_mute(self, audio=None, video=None):
        if not self.has_capability("mute"):
            print("Device does not support mute.")
            return False

        driver = self._get_driver_module()
        if not driver:
            print("No device configured.")
            return False

        return driver.set_mute(self.device, audio=audio, video=video)

