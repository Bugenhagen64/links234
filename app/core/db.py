# db.py

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "device.db")


# ---------------------------------------------------------
#  Connection helper
# ---------------------------------------------------------

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------
#  Device table
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

    cur.execute("DELETE FROM device")  # Only one device supported

    columns = ", ".join(device_dict.keys())
    placeholders = ", ".join("?" for _ in device_dict)
    values = list(device_dict.values())

    cur.execute(f"INSERT INTO device ({columns}) VALUES ({placeholders})", values)
    conn.commit()
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

    # Remove old row
    cur.execute("DELETE FROM status WHERE device_id = ?", (device_id,))

    # Insert new row
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
#  Generic helpers
# ---------------------------------------------------------

def get_all_devices():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM device")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


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

def ensure_schema():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS device (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        protocol TEXT,
        host TEXT,
        port INTEGER,
        serial_port TEXT
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

    conn.commit()
    conn.close()

