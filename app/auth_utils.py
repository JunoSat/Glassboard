import bcrypt


def hash_password(plain_text_password: str) -> str:
    """Generates a secure, salted cryptographic hash from a plain text password."""
    # Convert the string password into raw bytes
    password_bytes = plain_text_password.encode('utf-8')

    # Generate a unique random salt and hash the password
    # bcrypt automatically blends the salt into the final string
    salt = bcrypt.gensalt(rounds=12)  # 12 rounds is the industry standard balance of speed and security
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)

    # Decode the final byte string back into a standard UTF-8 text string to store in MySQL
    return hashed_bytes.decode('utf-8')


def verify_password(plain_text_password: str, stored_hash: str) -> bool:
    """Compares a plain text input password against a stored hash to check if they match."""
    password_bytes = plain_text_password.encode('utf-8')
    hash_bytes = stored_hash.encode('utf-8')

    # bcrypt extracts the salt automatically from the hash and checks the match safely
    return bcrypt.checkpw(password_bytes, hash_bytes)

                            