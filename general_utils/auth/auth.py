from argon2 import PasswordHasher


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2.

    :param password: The password to hash.
    :return: The hashed password.
    """
    ph = PasswordHasher()
    return ph.hash(password)


def verify_credential(password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hashed password.

    :param password: The plain text password to verify.
    :param hashed_password: The hashed password to verify against.
    :return: True if the password matches the hashed password, False otherwise.
    """
    ph = PasswordHasher()
    try:
        return ph.verify(hashed_password, password)
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False
