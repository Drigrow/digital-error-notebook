from cryptography.fernet import Fernet
from flask import current_app


def get_fernet():
    key = current_app.config.get("FERNET_KEY", "")
    if not key or key == "generate-a-key":
        key = Fernet.generate_key().decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_api_key(plain_key):
    f = get_fernet()
    return f.encrypt(plain_key.encode()).decode()


def decrypt_api_key(encrypted_key):
    f = get_fernet()
    return f.decrypt(encrypted_key.encode()).decode()
