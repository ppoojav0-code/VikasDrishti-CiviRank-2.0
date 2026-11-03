"""Local account authentication for Vikas Drishti.
New self-registered accounts are activated immediately; no email/SMS OTP is used.
"""
import sqlite3, hashlib, secrets
from pathlib import Path

DB_PATH = Path('data/vikas_drishti_accounts.db')

def _db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, contact TEXT UNIQUE NOT NULL,
        contact_type TEXT NOT NULL, verified INTEGER NOT NULL DEFAULT 1,
        role TEXT NOT NULL DEFAULT 'Data Analyst & Viewer', created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    con.commit()
    return con

def _hash(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 180000).hex()
    return f'{salt}${digest}'

def _check(password, stored):
    try:
        salt, digest = stored.split('$', 1)
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 180000).hex()
        return secrets.compare_digest(actual, digest)
    except Exception:
        return False

def create_account(username, password, contact, contact_type='Email'):
    """Create an immediately active account; contact is collected but not verified."""
    username = (username or '').strip()
    contact = (contact or '').strip()
    if len(username) < 3:
        return False, 'Username must be at least 3 characters.'
    if len(password or '') < 8:
        return False, 'Password must be at least 8 characters.'
    if not contact:
        return False, 'Enter an email address or phone number.'
    if contact_type not in ('Email', 'Phone'):
        contact_type = 'Email'
    con = _db()
    try:
        con.execute('INSERT INTO accounts(username,password_hash,contact,contact_type,verified,role) VALUES(?,?,?,?,1,?)',
                    (username, _hash(password), contact, contact_type, 'Data Analyst & Viewer'))
        con.commit()
        return True, 'Account created successfully.'
    except sqlite3.IntegrityError:
        return False, 'That username or email/phone is already registered.'
    finally:
        con.close()

def authenticate(username, password):
    con = _db()
    try:
        row = con.execute('SELECT username,password_hash,role FROM accounts WHERE username=?',
                          ((username or '').strip(),)).fetchone()
        if not row or not _check(password or '', row[1]):
            return False, 'The username or password is incorrect.', None
        return True, 'Signed in successfully.', {'username': row[0], 'role': row[2]}
    finally:
        con.close()


def ensure_demo_accounts():
    """Create predictable local demo logins once; never overwrite an existing account."""
    demo_accounts = [
        ("admin", "Admin@123", "Administrator"),
        ("administrator", "Admin@123", "Administrator"),
        ("viewer", "Viewer@123", "Viewer"),
        ("ngo", "Ngo@123", "NGO"),
        ("dataanalyst", "Analyst@123", "Data Analyst"),
    ]
    con = _db()
    try:
        for username, password, role in demo_accounts:
            exists = con.execute("SELECT 1 FROM accounts WHERE username=?", (username,)).fetchone()
            if not exists:
                contact = f"{username}@demo.vikasdrishti.local"
                con.execute(
                    "INSERT INTO accounts(username,password_hash,contact,contact_type,verified,role) VALUES(?,?,?,?,1,?)",
                    (username, _hash(password), contact, "Email", role),
                )
        con.commit()
    finally:
        con.close()
