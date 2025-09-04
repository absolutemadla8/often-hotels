from typing import Any, Dict, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, *, username: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        create_data = obj_in.dict()
        create_data.pop("password")
        create_data.pop("confirm_password")
        db_obj = User(
            **create_data,
            hashed_password=get_password_hash(obj_in.password)
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]
    ) -> User:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        if "password" in update_data:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
            
        return await super().update(db, db_obj=db_obj, obj_in=update_data)

    async def authenticate(
        self, db: AsyncSession, *, email: str, password: str
    ) -> Optional[User]:
        user = await self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def is_active(self, user: User) -> bool:
        return user.is_active

    async def is_superuser(self, user: User) -> bool:
        return user.is_superuser

    async def is_verified(self, user: User) -> bool:
        return user.is_verified

    async def verify_user(self, db: AsyncSession, *, user: User) -> User:
        user.is_verified = True
        user.email_verification_token = None
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def deactivate_user(self, db: AsyncSession, *, user: User) -> User:
        user.is_active = False
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def activate_user(self, db: AsyncSession, *, user: User) -> User:
        user.is_active = True
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def set_password_reset_token(
        self, db: AsyncSession, *, user: User, token: str
    ) -> User:
        user.password_reset_token = token
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def update_last_login(self, db: AsyncSession, *, user: User) -> User:
        from datetime import datetime
        user.last_login = datetime.utcnow()
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


user = CRUDUser(User)