# utils/password_manager.py
"""
Secure password handling using PBKDF2 with random salt.
Stores the hash in app_config.json under the "password_hash" key.
Backward compatible with older unsalted SHA‑256 hashes and auto‑upgrades them.
"""

import os
import hashlib
import json
import logging
from config import APP_CONFIG_FILE

logger = logging.getLogger(__name__)

# Recommended PBKDF2 iterations (OWASP 2023)
_PBKDF2_ITERATIONS = 600_000

# Minimum password length to avoid obviously weak passwords
_MIN_PASSWORD_LENGTH = 4


def _load_config():
    """Load application settings from APP_CONFIG_FILE.  Returns empty dict on failure."""
    if os.path.exists(APP_CONFIG_FILE):
        try:
            with open(APP_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error("Failed to load config file %s: %s", APP_CONFIG_FILE, e)
    return {}


def _save_config(config):
    """Save application settings to APP_CONFIG_FILE, creating parent dirs if needed."""
    try:
        os.makedirs(os.path.dirname(APP_CONFIG_FILE), exist_ok=True)
        with open(APP_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
    except IOError as e:
        logger.error("Could not write config file %s: %s", APP_CONFIG_FILE, e)
        raise


def _hash_password(password: str) -> str:
    """
    Generate a secure salted hash of the password.
    Format: 'salt_hex:key_hex'
    """
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'), salt, _PBKDF2_ITERATIONS
    )
    return salt.hex() + ':' + key.hex()


def is_password_set() -> bool:
    """Return True if a password hash exists in the config."""
    return 'password_hash' in _load_config()


def check_password(password: str) -> bool:
    """
    Verify the given password against the stored hash.
    Supports new salted PBKDF2 and legacy unsalted SHA‑256.
    If a legacy hash is matched, it is automatically upgraded to the new format.
    """
    config = _load_config()
    stored = config.get('password_hash')
    if not stored:
        # No password set – allow access
        return True

    # New salted format: 'salt_hex:key_hex'
    if ':' in stored:
        try:
            salt_hex, key_hex = stored.split(':')
            salt = bytes.fromhex(salt_hex)
            key = bytes.fromhex(key_hex)
            new_key = hashlib.pbkdf2_hmac(
                'sha256', password.encode('utf-8'), salt, _PBKDF2_ITERATIONS
            )
            if new_key == key:
                return True
            # Also try legacy iteration count (100k) if different? For compatibility if old code
            # but we won't auto-downgrade. We'll attempt a second check with 100k for migration.
            if _PBKDF2_ITERATIONS != 100_000:
                # Try old iteration count (used before upgrade)
                new_key_old = hashlib.pbkdf2_hmac(
                    'sha256', password.encode('utf-8'), salt, 100_000
                )
                if new_key_old == key:
                    # Re-hash with new iteration count and save
                    config['password_hash'] = _hash_password(password)
                    _save_config(config)
                    logger.info("Password hash upgraded to %d iterations.", _PBKDF2_ITERATIONS)
                    return True
            return False
        except (ValueError, KeyError) as e:
            logger.error("Invalid password hash format: %s", e)
            return False
    else:
        # Legacy unsalted SHA‑256
        if hashlib.sha256(password.encode()).hexdigest() == stored:
            # Upgrade to new salted format
            config['password_hash'] = _hash_password(password)
            _save_config(config)
            logger.info("Legacy password hash upgraded to PBKDF2.")
            return True
        return False


def set_password(new_password: str, force: bool = False):
    """
    Set or update the application password (hashed with salt).
    If `force` is False, a warning is logged if the password is too short.
    """
    if len(new_password) < _MIN_PASSWORD_LENGTH:
        logger.warning(
            "Password length (%d) is less than recommended minimum of %d.",
            len(new_password), _MIN_PASSWORD_LENGTH
        )
    config = _load_config()
    config['password_hash'] = _hash_password(new_password)
    _save_config(config)


def remove_password():
    """Remove the password protection entirely."""
    config = _load_config()
    if 'password_hash' in config:
        del config['password_hash']
        _save_config(config)


def change_password(old_password: str, new_password: str) -> bool:
    """Change the password after verifying the old one."""
    if not check_password(old_password):
        return False
    set_password(new_password, force=True)  # force to bypass weak password warning during change
    return True