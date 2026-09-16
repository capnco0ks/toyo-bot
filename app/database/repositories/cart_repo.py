from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import CartItem, Product


class CartRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_cart(self, user_id: int) -> List[CartItem]:
        stmt = (
            select(CartItem)
            .options(
                selectinload(CartItem.product).selectinload(Product.category)
            )
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_cart_item(self, user_id: int, product_id: int) -> Optional[CartItem]:
        stmt = (
            select(CartItem)
            .options(selectinload(CartItem.product))
            .where(CartItem.user_id == user_id, CartItem.product_id == product_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_or_update_item(self, user_id: int, product_id: int, quantity: int) -> CartItem:
        if quantity <= 0:
            quantity = 1
        item = await self.get_cart_item(user_id, product_id)
        if item:
            item.quantity += quantity
        else:
            item = CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
            self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def set_item_quantity(self, user_id: int, product_id: int, quantity: int) -> Optional[CartItem]:
        item = await self.get_cart_item(user_id, product_id)
        if not item:
            if quantity > 0:
                item = CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
                self.session.add(item)
                await self.session.commit()
                await self.session.refresh(item)
                return item
            return None

        if quantity <= 0:
            await self.session.delete(item)
            await self.session.commit()
            return None

        item.quantity = quantity
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def remove_item(self, user_id: int, product_id: int) -> bool:
        item = await self.get_cart_item(user_id, product_id)
        if item:
            await self.session.delete(item)
            await self.session.commit()
            return True
        return False

    async def clear_cart(self, user_id: int) -> None:
        stmt = delete(CartItem).where(CartItem.user_id == user_id)
        await self.session.execute(stmt)
        await self.session.commit()
