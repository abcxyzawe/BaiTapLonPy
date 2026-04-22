import hashlib


def hash_password(pw: str) -> str:
    """hash mk bang sha256, de demo cho don gian"""
    return hashlib.sha256(pw.encode('utf-8')).hexdigest()


def verify_password(plain: str, stored: str) -> bool:
    """so sanh mk - chap nhan ca stored dang plain (seed ban dau)
    hoac hashed (da qua update)
    """
    if stored == plain:
        return True
    return stored == hash_password(plain)
