# app/polling.py

import time
import traceback
from app.core.device_manager import DeviceManager
import app.core.db as db

def polling_loop(interval=2):
    print(f"[POLLING] Started (interval={interval}s)")

    while True:
        try:
            dm = DeviceManager()
            driver = dm._get_driver_module()

            if not dm.device or not driver:
                print("[POLLING] No device configured, sleeping...")
                time.sleep(interval)
                continue

            # Driver must implement get_status()
            info = driver.get_status(dm.device)

            current = db.get_status(dm.device["id"])

            # Update DB fields
            for key, value in info.items():
                if current[key] != value:
                    db.update_status_field(dm.device["id"], key, value)

            # NEW: update last_seen timestamp
            db.update_last_seen(dm.device["id"])

        except Exception as e:
            print("[POLLING] Error:", e)
            traceback.print_exc()

        time.sleep(interval)

if __name__ == "__main__":
    polling_loop()

