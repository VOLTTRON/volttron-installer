import random
import string

def generate_unique_uid(length=7) -> str:
    characters = string.ascii_letters + string.digits
    new_uid = ''.join(random.choice(characters) for _ in range(length))
    return new_uid