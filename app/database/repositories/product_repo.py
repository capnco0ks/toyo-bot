from typing import List, Optional
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Product, OrderItem


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, product_id: int) -> Optional[Product]:
        stmt = (
            select(Product)
            .options(selectinload(Product.category))
            .where(Product.id == product_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Product]:
        stmt = select(Product).where(Product.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_category(
        self,
        category_id: int,
        only_active: bool = True,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Product]:
        stmt = (
            select(Product)
            .options(selectinload(Product.category))
            .where(Product.category_id == category_id)
        )
        if only_active:
            stmt = stmt.where(Product.is_active.is_(True))
        stmt = stmt.order_by(Product.name.asc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_category(self, category_id: int, only_active: bool = True) -> int:
        stmt = select(func.count(Product.id)).where(Product.category_id == category_id)
        if only_active:
            stmt = stmt.where(Product.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def search(
        self,
        query: str,
        only_active: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Product]:
        q = f"%{query.strip().lower()}%"
        stmt = (
            select(Product)
            .options(selectinload(Product.category))
            .where(
                or_(
                    func.lower(Product.name).like(q),
                    func.lower(Product.article).like(q),
                    func.lower(Product.viscosity).like(q),
                    func.lower(Product.package).like(q),
                    func.lower(Product.description).like(q),
                )
            )
        )
        if only_active:
            stmt = stmt.where(Product.is_active.is_(True))
        stmt = stmt.order_by(Product.name.asc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_search(self, query: str, only_active: bool = True) -> int:
        q = f"%{query.strip().lower()}%"
        stmt = select(func.count(Product.id)).where(
            or_(
                func.lower(Product.name).like(q),
                func.lower(Product.article).like(q),
                func.lower(Product.viscosity).like(q),
                func.lower(Product.package).like(q),
                func.lower(Product.description).like(q),
            )
        )
        if only_active:
            stmt = stmt.where(Product.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def create(
        self,
        category_id: int,
        name: str,
        price: float,
        article: Optional[str] = None,
        viscosity: Optional[str] = None,
        volume: Optional[str] = None,
        package: Optional[str] = None,
        description: Optional[str] = None,
        photo_file_id: Optional[str] = None,
        min_order_quantity: int = 1,
        step_quantity: int = 1,
        is_active: bool = True,
    ) -> Product:
        product = Product(
            category_id=category_id,
            name=name.strip(),
            price=price,
            article=article.strip() if article else None,
            viscosity=viscosity.strip() if viscosity else None,
            volume=volume.strip() if volume else None,
            package=package.strip() if package else None,
            description=description.strip() if description else None,
            photo_file_id=photo_file_id,
            min_order_quantity=min_order_quantity,
            step_quantity=step_quantity,
            is_active=is_active,
        )
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def update_price(self, product_id: int, new_price: float) -> Optional[Product]:
        product = await self.get_by_id(product_id)
        if product:
            product.price = new_price
            await self.session.commit()
            await self.session.refresh(product)
        return product

    async def toggle_active(self, product_id: int) -> Optional[Product]:
        product = await self.get_by_id(product_id)
        if product:
            product.is_active = not product.is_active
            await self.session.commit()
            await self.session.refresh(product)
        return product

    async def delete_or_deactivate(self, product_id: int) -> bool:
        """
        Deletes the product if not referenced in any past orders,
        otherwise sets is_active=False to preserve historical order logs.
        """
        product = await self.get_by_id(product_id)
        if not product:
            return False

        # Check if product is in any past orders
        stmt = select(func.count(OrderItem.id)).where(OrderItem.product_id == product_id)
        result = await self.session.execute(stmt)
        orders_count = result.scalar_one() or 0

        if orders_count > 0:
            product.is_active = False
            await self.session.commit()
        else:
            await self.session.delete(product)
            await self.session.commit()
        return True
