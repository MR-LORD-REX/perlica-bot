from cryptography.fernet import Fernet

from bot.config.config import FERNET_KEY

cipher=Fernet(
    FERNET_KEY.encode()
)

def encrypt_token(token:str)->str:
    return cipher.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token:str)-> str:
    return cipher.decrypt(encrypted_token.encode()).decode()