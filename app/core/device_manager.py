# device_manager.py

import app.core.db as db
from importlib import import_module


class DeviceManager:
    def __init__(self):
        db.ensure_schema() 
        # Load device from DB (may be None)
        self.device = db.get_device()

    # ---------------------------------------------------------
    #  Driver loader
    # ---------------------------------------------------------

    def _get_driver_module(self):
        """
        Loads the correct driver module based on device protocol.
        Returns the module or None if no device is configured.
        """

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
        """
        Attempts to discover the device using the configured protocol.
        Returns True if discovery succeeded, False otherwise.
        """

        if not self.device:
            print("No device configured. Run setup first.")
            return False

        print("Starting discovery...")

        driver = self._get_driver_module()
        if not driver:
            print("No valid driver available.")
            return False

        # Serial discovery
        if "serial_port" in self.device and self.device["serial_port"]:
            try:
                info = driver.discover_serial(self.device["serial_port"])
                if info:
                    db.update_status(self.device["id"], info)
                    return True
            except Exception as e:
                print("Serial discovery failed:", e)

        # Network discovery
        if "host" in self.device and self.device["host"]:
            try:
                info = driver.discover_net(self.device["host"], self.device["port"])
                if info:
                    db.update_status(self.device["id"], info)
                    return True
            except Exception as e:
                print("Network discovery failed:", e)

        print("Discovery failed.")
        return False

    # ---------------------------------------------------------
    #  Status
    # ---------------------------------------------------------

    def get_status(self):
        """
        Returns the latest known status.
        If no device is configured, returns None.
        """

        if not self.device:
            print("No device configured. Run setup first.")
            return None

        # Try discovery first
        if not self.discover():
            return None

        return db.get_status(self.device["id"])

    # ---------------------------------------------------------
    #  Commands
    # ---------------------------------------------------------

    def set_power(self, state):
        driver = self._get_driver_module()
        if not driver:
            print("No device configured.")
            return False

        ok = driver.set_power(self.device, state)
        if ok:
            db.update_status_field(self.device["id"], "power", state)
        return ok

    def set_input(self, code):
        driver = self._get_driver_module()
        if not driver:
            print("No device configured.")
            return False

        ok = driver.set_input(self.device, code)
        if ok:
            db.update_status_field(self.device["id"], "input", code)
        return ok

    def volume_change(self, delta):
        driver = self._get_driver_module()
        if not driver:
            print("No device configured.")
            return False

        ok = driver.volume_change(self.device, delta)
        if ok:
            status = db.get_status(self.device["id"])
            new_vol = (status.get("volume") or 0) + delta
            db.update_status_field(self.device["id"], "volume", new_vol)
        return ok

    def set_mute(self, audio=None, video=None):
        driver = self._get_driver_module()
        if not driver:
            print("No device configured.")
            return False

        ok = driver.set_mute(self.device, audio=audio, video=video)
        if ok:
            if audio is not None:
                db.update_status_field(self.device["id"], "audio_mute", audio)
            if video is not None:
                db.update_status_field(self.device["id"], "video_mute", video)
        return ok
