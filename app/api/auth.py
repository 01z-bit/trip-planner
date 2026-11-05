from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User
from app.api.deps import get_current_user
from app.schemas import UserCreate, UserLogin, UserResponse, Token
from app.security import get_password_hash, verify_password, create_access_token

# 创建路由实例
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, summary="用户注册")
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # 1. 检查邮箱是否已经被注册
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册"
        )
    
    # 2. 对密码进行加密（绝不存明文）
    hashed_pwd = get_password_hash(user_in.password)
    
    # 3. 创建用户对象
    new_user = User(
        email=user_in.email,
        password_hash=hashed_pwd,
        display_name=user_in.display_name or user_in.email.split("@")[0] # 默认昵称为邮箱前缀
    )
    
    # 4. 保存到数据库
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user) # 刷新获取数据库生成的 ID 和时间
    
    return new_user

@router.post("/login", response_model=Token, summary="用户登录")
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    # 1. 查找用户
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()
    
    # 2. 校验用户是否存在，以及密码是否正确
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该账号已被禁用"
        )

    # 3. 生成 JWT Token，把用户 ID 塞进去
    access_token = create_access_token(data={"sub": user.id})
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse, summary="获取当前登录用户信息")
async def read_users_me(current_user: User = Depends(get_current_user)):
    # 如果代码能走到这里，说明 Token 验证通过了，current_user 就是数据库里的用户对象
    return current_user