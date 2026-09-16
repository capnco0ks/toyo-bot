from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Category, Product


class CategoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_active(self) -> List[Category]:
        stmt = (
            select(Category)
            .where(Category.is_active.is_(True))
            .order_by(Category.sort_order.asc(), Category.name.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all(self) -> List[Category]:
        stmt = select(Category).order_by(Category.sort_order.asc(), Category.name.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, category_id: int) -> Optional[Category]:
        stmt = select(Category).where(Category.id == category_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Category]:
        stmt = select(Category).where(func.lower(Category.name) == name.strip().lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_category(self, name: str, sort_order: int = 0) -> Category:
        existing = await self.get_by_name(name)
        if existing:
            return existing
        category = Category(name=name.strip(), sort_order=sort_order, is_active=True)
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def get_product_count_by_category(self, category_id: int, only_active: bool = True) -> int:
        stmt = select(func.count(Product.id)).where(Product.category_id == category_id)
        if only_active:
            stmt = stmt.where(Product.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0
