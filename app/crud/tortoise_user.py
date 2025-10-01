from typing import Optional
from app.models.models import User, RefreshToken
from app.core.security import get_password_hash, verify_password

class TortoiseUserCRUD:
    async def get_by_email(self, email: str) -> Optional[User]:
        return await User.get_or_none(email=email)

    async def get_by_id(self, user_id: int) -> Optional[User]:
        return await User.get_or_none(id=user_id)

    async def create(self, obj_in) -> User:
        # Handle both direct field arguments and schema objects
        if hasattr(obj_in, 'email'):
            # Schema object
            user_data = {
                'email': obj_in.email,
                'hashed_password': get_password_hash(obj_in.password),
                'full_name': getattr(obj_in, 'full_name', None) or f"{getattr(obj_in, 'first_name', '')} {getattr(obj_in, 'last_name', '')}".strip(),
                'is_active': True,
                'is_superuser': False
            }
        else:
            # Direct arguments (legacy support)
            user_data = obj_in
            if 'password' in user_data:
                user_data['hashed_password'] = get_password_hash(user_data.pop('password'))
                
        user = await User.create(**user_data)
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