"""Ed25519 signing helpers. Private keys are Fernet-encrypted at rest with KEY_ENCRYPTION_KEY."""
import base64
import hashlib
import json
import secrets

from cryptography.exceptions import InvalidSignature
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from django.conf import settings


def _fernet():
    return Fernet(settings.KEY_ENCRYPTION_KEY.encode())


def generate_keypair():
    """Returns (key_id, public_key_b64, encrypted_private_key)."""
    private = Ed25519PrivateKey.generate()
    raw_private = private.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    raw_public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    encrypted = _fernet().encrypt(raw_private).decode()
    return f'k-{secrets.token_hex(6)}', base64.b64encode(raw_public).decode(), encrypted


def canonical_json(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def hash_payload(payload):
    return hashlib.sha256(canonical_json(payload).encode()).hexdigest()


def sign_hash(encrypted_private_key, payload_hash):
    raw = _fernet().decrypt(encrypted_private_key.encode())
    private = Ed25519PrivateKey.from_private_bytes(raw)
    return base64.b64encode(private.sign(payload_hash.encode())).decode()


def verify_signature(public_key_b64, signature_b64, payload_hash):
    try:
        public = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
        public.verify(base64.b64decode(signature_b64), payload_hash.encode())
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False
