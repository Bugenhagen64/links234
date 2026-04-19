# db.py

import sqlite3
import os
from importlib import import_module
from datetime import datetime
from zoneinfo import ZoneInfo

DB_PATH = os.path.join(os.path.dirname(__file__), "device.db")


# ---------------------------------------------------------
#  Connection helper
# ---------------------------------------------------------

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------
#  Device table (only ONE device supported)
# ---------------------------------------------------------

def get_device():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM device LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def save_device(device_dict):
    """
    device_dict must contain:
    protocol, host, port, serial_port, etc.
    """

    conn = get_connection()
    cur = conn.cursor()

    # Remove old device (only one supported)
    cur.execute("DELETE FROM device")

    # Insert new device
    columns = ", ".join(device_dict.keys())
    placeholders = ", ".join("?" for _ in device_dict)
    values = list(device_dict.values())

    cur.execute(f"INSERT INTO device ({columns}) VALUES ({placeholders})", values)
    conn.commit()

    # Get new device ID
    device_id = cur.lastrowid

    # --- Save capabilities from driver ---
    try:
        protocol = device_dict.get("protocol")
        if protocol:
            module = import_module(f"app.drivers.{protocol}_driver")

            # Clear old capabilities
            clear_capabilities(device_id)

            # Save new capabilities
            if hasattr(module, "capabilities"):
                for cap in module.capabilities:
                    add_capability(device_id, cap)
            else:
                print(f"Driver {protocol} has no capabilities attribute")

    except Exception as e:
        print("Failed to load capabilities:", e)

    conn.close()


# ---------------------------------------------------------
#  Status table
# ---------------------------------------------------------

def get_status(device_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM status WHERE device_id = ?", (device_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_status(device_id, status_dict):
    """
    Replace entire status row.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM status WHERE device_id = ?", (device_id,))

    status_dict = {"device_id": device_id, **status_dict}
    columns = ", ".join(status_dict.keys())
    placeholders = ", ".join("?" for _ in status_dict)
    values = list(status_dict.values())

    cur.execute(f"INSERT INTO status ({columns}) VALUES ({placeholders})", values)
    conn.commit()
    conn.close()


def update_status_field(device_id, field, value):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE status SET {field} = ? WHERE device_id = ?",
        (value, device_id),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------
#  Capabilities
# ---------------------------------------------------------

def get_capabilities(device_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT capability FROM capabilities WHERE device_id = ?",
        (device_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return [row[0] for row in rows]


def add_capability(device_id, capability):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO capabilities (device_id, capability) VALUES (?, ?)",
        (device_id, capability)
    )
    conn.commit()
    conn.close()


def clear_capabilities(device_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM capabilities WHERE device_id = ?",
        (device_id,)
    )
    conn.commit()
    conn.close()

def save_capabilities(device_id, capabilities):
    conn = get_connection()
    cur = conn.cursor()

    # Rensa gamla capabilities
    cur.execute("DELETE FROM capabilities WHERE device_id = ?", (device_id,))

    # Lägg in nya
    for cap in capabilities:
        cur.execute(
            "INSERT INTO capabilities (device_id, capability) VALUES (?, ?)",
            (device_id, cap)
        )

    conn.commit()
    conn.close()

# ---------------------------------------------------------
#  Inputs
# ---------------------------------------------------------

def get_inputs(device_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM inputs WHERE device_id = ?", (device_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_input(device_id, name, code):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO inputs (device_id, name, code) VALUES (?, ?, ?)",
        (device_id, name, code),
    )
    conn.commit()
    conn.close()


def delete_input(device_id, code):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM inputs WHERE device_id = ? AND code = ?",
        (device_id, code),
    )
    conn.commit()
    conn.close()

def save_inputs(device_id, inputs):
    conn = get_connection()
    cur = conn.cursor()

    # Rensa gamla inputs
    cur.execute("DELETE FROM inputs WHERE device_id = ?", (device_id,))

    # Lägg in nya
    for inp in inputs:
        cur.execute(
            "INSERT INTO inputs (device_id, name, code) VALUES (?, ?, ?)",
            (device_id, inp["name"], inp["code"])
        )

    conn.commit()
    conn.close()

# ---------------------------------------------------------
#  Schema
# ---------------------------------------------------------

def ensure_schema():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS device (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        protocol TEXT NOT NULL,
        host TEXT,
        port INTEGER,
        serial_port TEXT,
        manufacturer TEXT,
        model TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS status (
        device_id INTEGER,
        power TEXT,
        input TEXT,
        volume INTEGER,
        audio_mute INTEGER,
        video_mute INTEGER,
        last_seen TEXT,
        FOREIGN KEY(device_id) REFERENCES device(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS inputs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id INTEGER,
        name TEXT,
        code TEXT,
        FOREIGN KEY(device_id) REFERENCES device(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS capabilities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id INTEGER NOT NULL,
        capability TEXT NOT NULL,
        FOREIGN KEY(device_id) REFERENCES device(id)
    )
    """)

    conn.commit()
    conn.close()

def update_last_seen(device_id):
    # Använd lokal tid med timezone
    now = datetime.now(ZoneInfo("Europe/Stockholm")).isoformat()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE status SET last_seen = ? WHERE device_id = ?",
        (now, device_id)
    )
    conn.commit()
    conn.close()

def reset_db(keep_site_room=False):
    """
    Deletes the database file and recreates an empty schema.
    keep_site_room is ignored (kept for CLI compatibility).
    """
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    # Recreate schema
    ensure_schema()


def update_device_field(device_id, field, value):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE device SET {field} = ? WHERE id = ?",
        (value, device_id)
    )
    conn.commit()
    conn.close()
