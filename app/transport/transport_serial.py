import serial

def send_serial(port, payload, timeout=5, baudrate=9600):
    """
    Skicka och ta emot råa bytes över RS232.
    Returnerar svaret som str.
    """
    ser = serial.Serial(
        port=port,
        baudrate=baudrate,
        timeout=timeout
    )

    try:
        ser.write(payload.encode("utf-8"))
        ser.flush()

        data = ser.read(4096)
        return data.decode("utf-8", errors="ignore")

    finally:
        ser.close()
