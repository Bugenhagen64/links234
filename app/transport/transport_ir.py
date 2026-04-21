# app/transport/transport_ir.py

import serial
import time

def send_ir(port, ir_payload, timeout=2, baudrate=115200):
    """
    Skickar en IR-kod via en USB-IR-enhet som beter sig som en seriell port.

    ir_payload: str (t.ex. HEX, Pronto, eller enhetsspecifikt kommando)
    Returnerar True/False beroende på om sändningen lyckades.
    """

    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout
        )
    except Exception as e:
        print(f"IR: kunde inte öppna port {port}: {e}")
        return False

    try:
        # Skicka IR-kod
        ser.write(ir_payload.encode("utf-8"))
        ser.flush()

        # Vissa IR-enheter svarar med OK/ERR
        try:
            resp = ser.readline().decode("utf-8", errors="ignore").strip()
            if resp:
                return resp.lower() in ("ok", "sent", "done")
        except:
            pass

        # Om ingen respons → anta att det gick bra
        return True

    except Exception as e:
        print(f"IR: fel vid sändning: {e}")
        return False

    finally:
        ser.close()
