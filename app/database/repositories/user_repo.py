from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
        else:
            updated = False
            if user.username != username:
                user.username = username
                updated = True
            if user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if user.last_name != last_name:
                user.last_name = last_name
                updated = True
            if updated:
                await self.session.commit()
                await self.session.refresh(user)
        return user

    async def update_profile(
        self,
        user_id: int,
        full_name: str,
        company_name: Optional[str],
        phone: str,
        city: str,
        delivery_address: str,
    ) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if user:
            user.saved_full_name = full_name.strip()
            user.company_name = company_name.strip() if company_name and company_name.lower() not in ["нет", "-", "—"] else None
            user.phone = phone.strip()
            user.city = city.strip()
            user.delivery_address = delivery_address.strip()
            await self.session.commit()
            await self.session.refresh(user)
        return user

    async def update_field(self, user_id: int, field_name: str, value: Optional[str]) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if user:
            val_clean = value.strip() if value else None
            if field_name == "name":
                user.saved_full_name = val_clean
            elif field_name == "company":
                user.company_name = None if val_clean and val_clean.lower() in ["нет", "-", "—"] else val_clean
            elif field_name == "phone":
                user.phone = val_clean
            elif field_name == "city":
                user.city = val_clean
            elif field_name == "address":
                user.delivery_address = val_clean
            await self.session.commit()
            await self.session.refresh(user)
        return user
