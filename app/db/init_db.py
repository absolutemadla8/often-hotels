import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.crud.user import user
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.schemas.user import UserCreate


async def init_db() -> None:
    """
    Initialize database with superuser
    """
    async with AsyncSessionLocal() as session:
        # Create superuser
        superuser = await user.get_by_email(session, email=settings.FIRST_SUPERUSER)
        if not superuser:
            user_in = UserCreate(
                email=settings.FIRST_SUPERUSER,
                password=settings.FIRST_SUPERUSER_PASSWORD,
                confirm_password=settings.FIRST_SUPERUSER_PASSWORD,
                first_name="Super",
                last_name="Admin",
                is_superuser=True,
                is_verified=True,
                is_active=True
            )
            superuser = await user.create(session, obj_in=user_in)
            print(f"Superuser created: {superuser.email}")
        else:
            print(f"Superuser already exists: {superuser.email}")


if __name__ == "__main__":
    asyncio.run(init_db())