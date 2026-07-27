# utils/license.py
"""
License management – tamper‑resistant dual storage (DB + hidden file).
Uses config.TRIAL_PERIOD_DAYS and config.MAX_TRIAL_RECORDS.
"""

import datetime
import os
import json
import hmac
import hashlib
import base64
import uuid
from utils.logger import setup_logger
from config import (
    TRIAL_PERIOD_DAYS,
    MAX_TRIAL_RECORDS,
    HIDDEN_LICENSE_DIR,
    HIDDEN_LICENSE_FILE
)

logger = setup_logger('AI_Rebar.License')

SECRET_KEY = b'AiRebar2025!SecretKeyForLicenseSigning'
HIDDEN_SECRET = b'AIREBAR_HIDDEN_FILE_SECRET_2025'

HIDDEN_DIR = HIDDEN_LICENSE_DIR
HIDDEN_FILE = HIDDEN_LICENSE_FILE

LICENSE_TABLE = "license_info"


# ----------------------------------------------------------------------
# Database helpers
# ----------------------------------------------------------------------
def _ensure_db_table(db):
    """Create license table if missing – safe to call repeatedly."""
    db.execute(f"""
        CREATE TABLE IF NOT EXISTS {LICENSE_TABLE} (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """, commit=True)


def _db_get(db, key, default=None):
    """Fetch a value from license_info, creating table if needed."""
    _ensure_db_table(db)  # ensure table exists before query
    row = db.fetchone(f"SELECT value FROM {LICENSE_TABLE} WHERE key=?", (key,))
    return row[0] if row else default


def _db_set(db, key, value):
    """Store a value into license_info, creating table if needed."""
    _ensure_db_table(db)
    db.execute(
        f"INSERT OR REPLACE INTO {LICENSE_TABLE} (key, value) VALUES (?, ?)",
        (key, value),
        commit=True
    )


# ----------------------------------------------------------------------
# Machine ID
# ----------------------------------------------------------------------
def get_machine_id():
    try:
        mac = uuid.getnode()
        if mac == 0:
            raise OSError('No MAC')
        return f'mac-{mac:012x}'
    except Exception:
        fallback = os.path.join(os.path.expanduser('~'), '.airebar_mid')
        if os.path.exists(fallback):
            with open(fallback, 'r') as f:
                return f.read().strip()
        mid = str(uuid.uuid4())
        with open(fallback, 'w') as f:
            f.write(mid)
        return mid


# ----------------------------------------------------------------------
# Hidden file helpers
# ----------------------------------------------------------------------
def _read_hidden_file():
    if not os.path.exists(HIDDEN_FILE):
        return None
    try:
        with open(HIDDEN_FILE, 'rb') as f:
            raw = f.read()
        decoded = base64.urlsafe_b64decode(raw)
        data = json.loads(decoded.decode('utf-8'))
        signature = data.pop('signature', None)
        if not signature:
            return None
        msg = json.dumps(data, sort_keys=True).encode('utf-8')
        expected = hmac.new(HIDDEN_SECRET, msg, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            logger.warning("Hidden file signature mismatch – tampering detected.")
            return None
        data['signature'] = signature
        return data
    except Exception as e:
        logger.error("Hidden file corrupted: %s", e)
        return None


def _write_hidden_file(data):
    os.makedirs(HIDDEN_DIR, exist_ok=True)
    # Work on a copy to avoid mutating caller's dict
    payload = {k: v for k, v in data.items() if k != 'signature'}
    msg = json.dumps(payload, sort_keys=True).encode('utf-8')
    sig = hmac.new(HIDDEN_SECRET, msg, hashlib.sha256).hexdigest()
    payload['signature'] = sig
    encoded = base64.urlsafe_b64encode(json.dumps(payload, sort_keys=True).encode('utf-8'))
    with open(HIDDEN_FILE, 'wb') as f:
        f.write(encoded)


# ----------------------------------------------------------------------
# Core license functions
# ----------------------------------------------------------------------
def init_trial(db):
    """Initialize trial ONLY if no valid license exists in DB."""
    _ensure_db_table(db)   # ensure table exists

    # Check DB for an existing non-trial license first
    existing_type = _db_get(db, 'license_type')
    if existing_type and existing_type != 'trial':
        # License already activated; rebuild hidden file from DB
        _rebuild_hidden_from_db(db)
        return

    # Check if trial already started in DB (to prevent reset)
    trial_start_db = _db_get(db, 'trial_start')
    if trial_start_db:
        # Trial already exists in DB; just ensure hidden file matches
        _rebuild_hidden_from_db(db)
        return

    # No license at all → start a new trial
    today = datetime.date.today().isoformat()
    expiry = (datetime.date.today() + datetime.timedelta(days=TRIAL_PERIOD_DAYS)).isoformat()
    hidden_data = {
        'machine_id': get_machine_id(),
        'license_type': 'trial',
        'trial_start': today,
        'expiry_date': expiry
    }
    _write_hidden_file(hidden_data)
    _db_set(db, 'license_type', 'trial')
    _db_set(db, 'trial_start', today)
    _db_set(db, 'expiry_date', expiry)
    _db_set(db, 'record_count', '0')
    _db_set(db, 'max_records', str(MAX_TRIAL_RECORDS))
    logger.info("Trial started – expires %s or %d records", today, MAX_TRIAL_RECORDS)


def _rebuild_hidden_from_db(db):
    """Create hidden file from current DB license info."""
    lic_type = _db_get(db, 'license_type', 'trial')
    data = {
        'machine_id': _db_get(db, 'machine_id', get_machine_id()),
        'license_type': lic_type
    }
    if lic_type == 'trial':
        data['trial_start'] = _db_get(db, 'trial_start')
        data['expiry_date'] = _db_get(db, 'expiry_date')
    else:
        data['expiry_date'] = _db_get(db, 'expiry_date', None)
    _write_hidden_file(data)
    logger.info("Hidden file rebuilt from DB.")


def check_license(db):
    """Verify license validity. Returns True if usable, False otherwise."""
    # Ensure table exists before any DB access
    _ensure_db_table(db)

    hidden = _read_hidden_file()
    if hidden is None:
        # Try to restore from DB before falling back to trial
        db_type = _db_get(db, 'license_type')
        if db_type:
            _rebuild_hidden_from_db(db)
            hidden = _read_hidden_file()
        else:
            init_trial(db)
            hidden = _read_hidden_file()
        if hidden is None:
            return False

    lic_type = hidden.get('license_type', 'trial')
    if lic_type == 'unlimited':
        return True
    if lic_type in ('3month', '6month', '1year'):
        expiry_str = hidden.get('expiry_date') or _db_get(db, 'expiry_date')
        if expiry_str:
            expiry = datetime.date.fromisoformat(expiry_str)
            return datetime.date.today() <= expiry
        return False
    if lic_type == 'trial':
        trial_start_str = hidden.get('trial_start')
        if not trial_start_str:
            return False
        trial_start = datetime.date.fromisoformat(trial_start_str)
        expiry = trial_start + datetime.timedelta(days=TRIAL_PERIOD_DAYS)
        if datetime.date.today() > expiry:
            return False
        records = int(_db_get(db, 'record_count', '0'))
        max_rec = int(_db_get(db, 'max_records', str(MAX_TRIAL_RECORDS)))
        if records >= max_rec:
            return False
        return True
    return False


def increment_usage(db):
    """Increment usage counter for trial. Returns False if limit reached."""
    _ensure_db_table(db)   # ensure table exists
    hidden = _read_hidden_file()
    lic_type = hidden.get('license_type', 'trial') if hidden else 'trial'
    if lic_type != 'trial':
        return True
    current = int(_db_get(db, 'record_count', '0')) + 1
    _db_set(db, 'record_count', str(current))
    max_rec = int(_db_get(db, 'max_records', str(MAX_TRIAL_RECORDS)))
    if current >= max_rec:
        logger.info("Trial record limit reached.")
        return False
    return check_license(db)


def get_license_info(db):
    """Return a dict with license status information."""
    _ensure_db_table(db)   # ensure table exists
    hidden = _read_hidden_file()
    if not hidden:
        return {'type': 'none', 'remaining_days': -1, 'records_used': 0, 'max_records': 0}
    lic_type = hidden.get('license_type', 'trial')
    info = {'type': lic_type, 'remaining_days': -1, 'records_used': 0, 'max_records': 0}
    if lic_type == 'trial':
        start_str = hidden.get('trial_start', '')
        if start_str:
            start = datetime.date.fromisoformat(start_str)
            expiry = start + datetime.timedelta(days=TRIAL_PERIOD_DAYS)
            info['remaining_days'] = (expiry - datetime.date.today()).days
        info['records_used'] = int(_db_get(db, 'record_count', '0'))
        info['max_records'] = int(_db_get(db, 'max_records', str(MAX_TRIAL_RECORDS)))
    elif lic_type in ('3month', '6month', '1year'):
        expiry_str = hidden.get('expiry_date') or _db_get(db, 'expiry_date')
        if expiry_str:
            expiry = datetime.date.fromisoformat(expiry_str)
            info['remaining_days'] = (expiry - datetime.date.today()).days
    elif lic_type == 'unlimited':
        info['remaining_days'] = float('inf')
    return info


def activate_license(activation_key, db):
    """Validate and apply a purchased license key.
    Returns (success, message) tuple.
    """
    _ensure_db_table(db)   # ensure table exists
    try:
        raw = base64.urlsafe_b64decode(activation_key.encode('ascii')).decode('utf-8')
        parts = raw.split('|')
        if len(parts) != 5:
            return False, "Invalid key format."
        key_machine, lic_type, expiry_str, issued_str, signature = parts
        msg = f"{key_machine}|{lic_type}|{expiry_str}|{issued_str}".encode()
        expected = hmac.new(SECRET_KEY, msg, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            logger.error("Activation key signature mismatch")
            return False, "Key verification failed. Please check the code."
        if key_machine != get_machine_id():
            logger.error("Machine ID mismatch")
            return False, "This key is not valid for this machine."

        # Update hidden file
        hidden = _read_hidden_file() or {}
        hidden['license_type'] = lic_type
        hidden.pop('trial_start', None)
        if lic_type != 'unlimited':
            hidden['expiry_date'] = expiry_str
        else:
            hidden.pop('expiry_date', None)
        _write_hidden_file(hidden)

        # Update database
        _db_set(db, 'license_type', lic_type)
        _db_set(db, 'machine_id', key_machine)
        if lic_type != 'unlimited':
            _db_set(db, 'expiry_date', expiry_str)
        _db_set(db, 'record_count', '0')
        _db_set(db, 'max_records', '0')
        _db_set(db, 'trial_start', None)

        logger.info("License activated: %s", lic_type)
        return True, "License activated successfully! Restart may be required."
    except Exception as e:
        logger.error("Activation failed: %s", e)
        return False, f"An error occurred: {e}"


def format_license_status(db):
    info = get_license_info(db)
    ltype = info.get('type', 'unknown')
    rem = info.get('remaining_days', -1)
    name_map = {
        'trial': 'Trial',
        '3month': '3-Month',
        '6month': '6-Month',
        '1year': '1-Year',
        'unlimited': 'Unlimited'
    }
    display_type = name_map.get(ltype, ltype.title())
    if ltype == 'unlimited' or rem == float('inf'):
        return f"{display_type} (permanent)"
    elif rem <= 0:
        return "Expired"
    else:
        return f"{display_type} – {rem} day(s) left"