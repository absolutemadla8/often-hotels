from typing import Optional
from app.models.models import User, RefreshToken
from app.core.security import get_password_hash, verify_password

class TortoiseUserCRUD:
    async def get_by_email(self, email: str) -> Optional[User]:
        return await User.get_or_none(email=email)

    async def get_by_id(self, user_id: int) -> Optional[User]:
        return await User.get_or_none(id=user_id)

    async def create(self, email: str, username: str, password: str, full_name: str = None) -> User:
        user = await User.create(
            email=email,
            username=username,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            is_active=True
        )
        return user

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        user = await self.get_by_email(email=email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    async def is_active(self, user: User) -> bool:
        return user.is_active

    async def is_superuser(self, user: User) -> bool:
        return user.is_superuser

    async def update_password(self, user: User, new_password: str) -> User:
        user.hashed_password = get_password_hash(new_password)
        await user.save()
        return user

tortoise_user = TortoiseUserCRUD()