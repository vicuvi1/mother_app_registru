"""Criptare opțională pentru copii de rezervă (.db.enc)."""

from __future__ import annotations

import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MAGIC = b"RDBKENC1"
SALT_LEN = 16
KDF_ITERATIONS = 480_000


class BackupCryptoError(Exception):
    pass


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def encrypt_file(source: Path, dest: Path, passphrase: str) -> None:
    if not passphrase:
        raise BackupCryptoError("Parola este goală.")
    salt = os.urandom(SALT_LEN)
    token = Fernet(_derive_key(passphrase, salt)).encrypt(source.read_bytes())
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(MAGIC + salt + token)


def decrypt_file(source: Path, dest: Path, passphrase: str) -> None:
    raw = source.read_bytes()
    if not raw.startswith(MAGIC):
        raise BackupCryptoError("Fișier criptat invalid.")
    if len(raw) < len(MAGIC) + SALT_LEN + 1:
        raise BackupCryptoError("Fișier criptat prea scurt.")
    salt = raw[len(MAGIC) : len(MAGIC) + SALT_LEN]
    token = raw[len(MAGIC) + SALT_LEN :]
    try:
        plain = Fernet(_derive_key(passphrase, salt)).decrypt(token)
    except InvalidToken as exc:
        raise BackupCryptoError("Parolă incorectă sau fișier deteriorat.") from exc
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(plain)


def is_encrypted_backup(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(len(MAGIC)) == MAGIC
    except OSError:
        return False
