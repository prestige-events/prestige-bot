import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "prestige.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            psid TEXT UNIQUE NOT NULL,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts(id),
            UNIQUE(contact_id, tag)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            buyin TEXT,
            reentry TEXT,
            guaranteed TEXT,
            blinds TEXT,
            description TEXT,
            keyword TEXT,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            tournament_id INTEGER NOT NULL,
            status TEXT DEFAULT 'interested',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts(id),
            FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
            UNIQUE(contact_id, tournament_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER,
            direction TEXT NOT NULL,
            message_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            message_text TEXT NOT NULL,
            send_at TIMESTAMP NOT NULL,
            sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
        )
    """)

    conn.commit()
    conn.close()


# --- Contacts ---

def get_or_create_contact(psid, first_name=None, last_name=None):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM contacts WHERE psid = ?", (psid,))
    contact = c.fetchone()

    if contact is None:
        c.execute(
            "INSERT INTO contacts (psid, first_name, last_name) VALUES (?, ?, ?)",
            (psid, first_name, last_name),
        )
        conn.commit()
        contact_id = c.lastrowid
        add_tag(contact_id, "nuovo_contatto")
    else:
        contact_id = contact["id"]
        if first_name and not contact["first_name"]:
            c.execute(
                "UPDATE contacts SET first_name = ?, last_name = ? WHERE id = ?",
                (first_name, last_name, contact_id),
            )
            conn.commit()

    conn.close()
    return contact_id


def get_contact_by_psid(psid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM contacts WHERE psid = ?", (psid,))
    contact = c.fetchone()
    conn.close()
    return contact


def get_all_contacts():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT c.*, GROUP_CONCAT(t.tag) as tags
        FROM contacts c
        LEFT JOIN tags t ON c.id = t.contact_id
        GROUP BY c.id
        ORDER BY c.created_at DESC
    """)
    contacts = c.fetchall()
    conn.close()
    return contacts


# --- Tags ---

def add_tag(contact_id, tag):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT OR IGNORE INTO tags (contact_id, tag) VALUES (?, ?)",
            (contact_id, tag),
        )
        conn.commit()
    finally:
        conn.close()


def remove_tag(contact_id, tag):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "DELETE FROM tags WHERE contact_id = ? AND tag = ?", (contact_id, tag)
    )
    conn.commit()
    conn.close()


def get_contacts_by_tag(tag):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT c.* FROM contacts c
        JOIN tags t ON c.id = t.contact_id
        WHERE t.tag = ?
    """, (tag,))
    contacts = c.fetchall()
    conn.close()
    return contacts


def get_tags_for_contact(contact_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT tag FROM tags WHERE contact_id = ?", (contact_id,))
    tags = [row["tag"] for row in c.fetchall()]
    conn.close()
    return tags


# --- Tournaments ---

def create_tournament(name, date, time, buyin, reentry, guaranteed, blinds, description, keyword):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO tournaments (name, date, time, buyin, reentry, guaranteed, blinds, description, keyword)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, date, time, buyin, reentry, guaranteed, blinds, description, keyword.upper()))
    conn.commit()
    tournament_id = c.lastrowid
    conn.close()
    return tournament_id


def get_active_tournaments():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM tournaments WHERE active = 1 ORDER BY date ASC")
    tournaments = c.fetchall()
    conn.close()
    return tournaments


def get_tournament_by_id(tournament_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM tournaments WHERE id = ?", (tournament_id,))
    tournament = c.fetchone()
    conn.close()
    return tournament


def update_tournament(tournament_id, name, date, time, buyin, reentry, guaranteed, blinds, description, keyword):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        UPDATE tournaments SET name=?, date=?, time=?, buyin=?, reentry=?,
        guaranteed=?, blinds=?, description=?, keyword=?
        WHERE id=?
    """, (name, date, time, buyin, reentry, guaranteed, blinds, description, keyword.upper(), tournament_id))
    conn.commit()
    conn.close()


def delete_tournament(tournament_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM registrations WHERE tournament_id = ?", (tournament_id,))
    c.execute("DELETE FROM scheduled_messages WHERE tournament_id = ?", (tournament_id,))
    c.execute("DELETE FROM tournaments WHERE id = ?", (tournament_id,))
    conn.commit()
    conn.close()


def get_tournament_by_keyword(keyword):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM tournaments WHERE keyword = ? AND active = 1",
        (keyword.upper(),),
    )
    tournament = c.fetchone()
    conn.close()
    return tournament


# --- Registrations ---

def register_contact_to_tournament(contact_id, tournament_id, status="interested"):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT OR REPLACE INTO registrations (contact_id, tournament_id, status)
            VALUES (?, ?, ?)
        """, (contact_id, tournament_id, status))
        conn.commit()
    finally:
        conn.close()


def get_tournament_registrations(tournament_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT c.*, r.status FROM contacts c
        JOIN registrations r ON c.id = r.contact_id
        WHERE r.tournament_id = ?
    """, (tournament_id,))
    registrations = c.fetchall()
    conn.close()
    return registrations


# --- Message Log ---

def log_message(contact_id, direction, message_text):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages_log (contact_id, direction, message_text) VALUES (?, ?, ?)",
        (contact_id, direction, message_text),
    )
    conn.commit()
    conn.close()


# --- Scheduled Messages ---

def create_scheduled_message(tournament_id, tag, message_text, send_at):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO scheduled_messages (tournament_id, tag, message_text, send_at)
        VALUES (?, ?, ?, ?)
    """, (tournament_id, tag, message_text, send_at))
    conn.commit()
    conn.close()


def get_pending_scheduled_messages():
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        SELECT * FROM scheduled_messages
        WHERE sent = 0 AND send_at <= ?
    """, (now,))
    messages = c.fetchall()
    conn.close()
    return messages


def mark_scheduled_message_sent(message_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE scheduled_messages SET sent = 1 WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()
