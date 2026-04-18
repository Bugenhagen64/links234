def discover_serial(port):
    return {"power": "on", "input": "hdmi1", "volume": 10}

def discover_net(host, port):
    return {"power": "on", "input": "hdmi1", "volume": 10}

def set_power(device, state):
    print(f"[FAKE] Power set to {state}")
    return True

def set_input(device, code):
    print(f"[FAKE] Input set to {code}")
    return True

def volume_change(device, delta):
    print(f"[FAKE] Volume changed by {delta}")
    return True

def set_mute(device, audio=None, video=None):
    print(f"[FAKE] Mute changed audio={audio}, video={video}")
    return True
