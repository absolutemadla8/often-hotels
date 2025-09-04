from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.refresh_token import RefreshToken


class CRUDRefreshToken(CRUDBase[RefreshToken, dict, dict]):
    async def create_refresh_token(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        token: str,
        expires_in_minutes: int = 43200,  # 30 days
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> RefreshToken:
        expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        db_obj = RefreshToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_by_token(
        self, db: AsyncSession, *, token: str
    ) -> Optional[RefreshToken]:
        result = await db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.token == token,
                    RefreshToken.expires_at > datetime.utcnow()
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_user_tokens(
        self, db: AsyncSession, *, user_id: int
    ) -> List[RefreshToken]:
        result = await db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.expires_at > datetime.utcnow()
                )
            )
        )
        return result.scalars().all()

    async def revoke_token(
        self, db: AsyncSession, *, token: str
    ) -> bool:
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        refresh_token = result.scalar_one_or_none()
        if refresh_token:
            await db.delete(refresh_token)
            await db.commit()
            return True
        return False

    async def revoke_user_tokens(
        self, db: AsyncSession, *, user_id: int
    ) -> int:
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.user_id == user_id)
        )
        tokens = result.scalars().all()
        count = len(tokens)
        for token in tokens:
            await db.delete(token)
        await db.commit()
        return count

    async def cleanup_expired_tokens(self, db: AsyncSession) -> int:
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.expires_at <= datetime.utcnow()
            )
        )
        expired_tokens = result.scalars().all()
        count = len(expired_tokens)
        for token in expired_tokens:
            await db.delete(token)
        await db.commit()
        return count


refresh_token = CRUDRefreshToken(RefreshToken)