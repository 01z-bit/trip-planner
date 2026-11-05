import bcrypt
from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-super-secret-key-keep-it-safe"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# 1. 加密密码 (直接使用 bcrypt)
def get_password_hash(password: str) -> str:
    # bcrypt 只处理前 72 字节，超出部分会被自动截断，这是其设计特性
    pwd_bytes = password.encode('utf-8')[:72] 
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

# 2. 校验密码
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8')[:72], 
            hashed_password.encode('utf-8')
        )
    except ValueError:
        return False

# 3. 创建 JWT Token (保持不变)
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)