import socket

def send_tcp(host, port, payload, timeout=5):
    """
    Skicka och ta emot råa bytes över TCP.
    Returnerar svaret som str.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)

    try:
        sock.connect((host, port))
        sock.sendall(payload.encode("utf-8"))
        data = sock.recv(4096)
        return data.decode("utf-8", errors="ignore")

    finally:
        sock.close()
