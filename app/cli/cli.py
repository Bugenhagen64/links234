# cli.py

import argparse
import json
from app.core.device_manager import DeviceManager
import app.core.db as db


def main():
    parser = argparse.ArgumentParser(
        description="CLI-verktyg för att styra projektorn via DeviceManager"
    )

    sub = parser.add_subparsers(dest="command")

    # ---------------------------------------------------------
    #  setup (init + discovery + optional JSON export)
    # ---------------------------------------------------------
    p_setup = sub.add_parser("setup", help="Initiera device och kör discovery")
    p_setup.add_argument("--host", help="IP-adress till projektorn")
    p_setup.add_argument("--port", type=int, help="TCP-port (t.ex. 4352)")
    p_setup.add_argument("--password", help="Lösenord för nätverksprotokoll (t.ex. PJLink)")
    p_setup.add_argument("--serial", help="Serial-port (t.ex. /dev/ttyUSB0)")
    p_setup.add_argument("--json", help="Spara resultatet som JSON-fil")

    # ---------------------------------------------------------
    #  status
    # ---------------------------------------------------------
    sub.add_parser("status", help="Visa aktuell status")

    # ---------------------------------------------------------
    #  power on/off
    # ---------------------------------------------------------
    p_power = sub.add_parser("power", help="Slå på eller av projektorn")
    p_power.add_argument("state", choices=["on", "off"], help="on/off")

    # ---------------------------------------------------------
    #  input <code>
    # ---------------------------------------------------------
    p_input = sub.add_parser("input", help="Byt ingång")
    p_input.add_argument("code", help="Ingångskod (t.ex. 31, 32, 41)")

    # ---------------------------------------------------------
    #  volume +N / -N
    # ---------------------------------------------------------
    p_vol = sub.add_parser("volume", help="Ändra volym")
    p_vol.add_argument("delta", type=int, help="t.ex. +5 eller -3")

    # ---------------------------------------------------------
    #  mute audio/video
    # ---------------------------------------------------------
    p_mute = sub.add_parser("mute", help="Sätt mute")
    p_mute.add_argument("--audio", choices=["on", "off"])
    p_mute.add_argument("--video", choices=["on", "off"])

    args = parser.parse_args()

    # ---------------------------------------------------------
    #  SETUP
    # ---------------------------------------------------------
    if args.command == "setup":
        # 1. Rensa DB men behåll site/room
        db.reset_db(keep_site_room=True)

        # 2. Spara grundinfo
        info = {
            "timeout": 5,
            "reachable": 0
        }

        if args.host:
            info["host"] = args.host
        if args.port:
            info["port_net"] = args.port
        if args.password:
            info["password"] = args.password
        if args.serial:
            info["port_serial"] = args.serial

        db.save_device_info(**info)
        print("Grundinfo sparad:", info)

        # 3. Kör discovery
        dm = DeviceManager()
        ok = dm.discover()

        device = db.get_device()
        result = {
            "success": ok,
            "device": dict(device) if device else None,
            "inputs": [dict(i) for i in db.get_inputs(device["id"])] if ok else [],
            "capabilities": dict(db.get_capabilities(device["id"])) if ok else {}
        }

        print("Discovery:", "OK" if ok else "FAILED")
        print(json.dumps(result, indent=4))

        # 4. Exportera JSON om begärt
        if args.json:
            with open(args.json, "w") as f:
                json.dump(result, f, indent=4)
            print(f"Resultat sparat till {args.json}")

        return

    # ---------------------------------------------------------
    #  STATUS
    # ---------------------------------------------------------
    dm = DeviceManager()

    if args.command == "status":
        print(dm.get_status())
        return

    # ---------------------------------------------------------
    #  POWER
    # ---------------------------------------------------------
    if args.command == "power":
        print(dm.set_power(args.state))
        return

    # ---------------------------------------------------------
    #  INPUT
    # ---------------------------------------------------------
    if args.command == "input":
        print(dm.set_input(args.code))
        return

    # ---------------------------------------------------------
    #  VOLUME
    # ---------------------------------------------------------
    if args.command == "volume":
        print(dm.volume_change(args.delta))
        return

    # ---------------------------------------------------------
    #  MUTE
    # ---------------------------------------------------------
    if args.command == "mute":
        audio = None
        video = None

        if args.audio:
            audio = True if args.audio == "on" else False
        if args.video:
            video = True if args.video == "on" else False

        print(dm.set_mute(audio=audio, video=video))
        return

    parser.print_help()


if __name__ == "__main__":
    main()

