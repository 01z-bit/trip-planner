from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

# 注册时的请求体
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="密码至少6位")
    display_name: str | None = None

# 登录时的请求体
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# 返回给前端的用户信息（绝不包含密码）
class UserResponse(BaseModel):
    id: str
    email: EmailStr
    display_name: str | None = None
    is_active: bool

    class Config:
        from_attributes = True  # 允许从数据库对象直接转换

# 登录成功后返回的 Token
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TripCreate(BaseModel):
    title: str
    origin: str | None = None 
    destination: str
    start_date: str | None = None
    end_date: str | None = None
    budget: str | None = None

class TripResponse(BaseModel):
    id: str
    user_id: str
    title: str
    origin: str | None = None
    destination: str
    start_date: str | None = None
    end_date: str | None = None
    budget: str | None = None
    plan_json: str | None = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True