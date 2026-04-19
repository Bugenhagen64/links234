# cli.py

import argparse
import json
from app.core.device_manager import DeviceManager
import app.core.db as db


def main():
    parser = argparse.ArgumentParser(
        description="CLI-verktyg för att styra displayen via DeviceManager"
    )

    sub = parser.add_subparsers(dest="command")

    # ---------------------------------------------------------
    #  setup
    # ---------------------------------------------------------
    p_setup = sub.add_parser("setup", help="Initiera device och kör discovery")
    p_setup.add_argument("--protocol", required=True, help="Driver-protokoll (t.ex. fake, pjlink)")
    p_setup.add_argument("--host", help="IP-adress till enheten")
    p_setup.add_argument("--port", type=int, help="TCP-port")
    p_setup.add_argument("--serial", help="Serial-port (t.ex. /dev/ttyUSB0)")
    p_setup.add_argument("--json", help="Spara resultatet som JSON-fil")

    # ---------------------------------------------------------
    #  status
    # ---------------------------------------------------------
    sub.add_parser("status", help="Visa aktuell status")

    # ---------------------------------------------------------
    #  power on/off
    # ---------------------------------------------------------
    p_power = sub.add_parser("power", help="Slå på eller av enheten")
    p_power.add_argument("state", choices=["on", "off"], help="on/off")

    # ---------------------------------------------------------
    #  input <code>
    # ---------------------------------------------------------
    p_input = sub.add_parser("input", help="Byt ingång")
    p_input.add_argument("code", help="Ingångskod")

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
        db.reset_db()

        device_info = {
            "protocol": args.protocol,
            "host": args.host,
            "port": args.port,
            "serial_port": args.serial
        }

        device_info = {k: v for k, v in device_info.items() if v is not None}

        db.save_device(device_info)
        print("Device sparad:", device_info)

        dm = DeviceManager()
        ok = dm.discover()

        device = db.get_device()
        result = {
            "success": ok,
            "device": device,
            "status": db.get_status(device["id"]) if ok else None,
            "inputs": db.get_inputs(device["id"]) if ok else [],
            "capabilities": db.get_capabilities(device["id"]) if ok else []
        }

        print("Discovery:", "OK" if ok else "FAILED")
        print(json.dumps(result, indent=4))

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
        device = db.get_device()
        if not device:
            print("Ingen device konfigurerad. Kör först: setup")
            return

        device_id = device["id"]
        status = db.get_status(device_id)
        inputs = db.get_inputs(device_id)
        caps = db.get_capabilities(device_id)

        data = {
            "device": device,
            "status": status,
            "inputs": inputs,
            "capabilities": caps,
        }

        print("=== DEVICE ===")
        print(f"  Manufacturer: {device.get('manufacturer') or '-'}")
        print(f"  Model:        {device.get('model') or '-'}")
        print(f"  Protocol:     {device.get('protocol')}")
        print(f"  Host:         {device.get('host')}")
        print(f"  Port:         {device.get('port')}")
        print(f"  Serial port:  {device.get('serial_port')}")
        print()

        print("\n=== STATUS ===")
        if status:
            print(f"  Power:       {status.get('power')}")
            print(f"  Input:       {status.get('input')}")
            print(f"  Volume:      {status.get('volume')}")
            print(f"  Audio mute:  {status.get('audio_mute')}")
            print(f"  Video mute:  {status.get('video_mute')}")
            print(f"  Last seen:   {status.get('last_seen')}")
        else:
            print("  (ingen status)")

        print("\n=== INPUTS ===")
        if inputs:
            for inp in inputs:
                print(f"  {inp['code']:>3}   {inp['name']}")
        else:
            print("  (inga inputs)")

        print("\n=== CAPABILITIES ===")
        if caps:
            print("  " + ", ".join(caps))
        else:
            print("  (inga capabilities)")

        print("\n=== JSON ===")
        print(json.dumps(data, indent=4))
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
            audio = args.audio == "on"
        if args.video:
            video = args.video == "on"

        print(dm.set_mute(audio=audio, video=video))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
