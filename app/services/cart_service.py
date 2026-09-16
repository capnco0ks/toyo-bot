from typing import Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.cart_repo import CartRepository
from app.database.models import CartItem


class CartService:
    def __init__(self, session: AsyncSession):
        self.repo = CartRepository(session)

    async def get_cart_summary(self, user_id: int) -> Tuple[List[CartItem], float, int, int]:
        """
        Returns (items, total_amount, total_count, total_positions)
        """
        items = await self.repo.get_user_cart(user_id)
        total_amount = 0.0
        total_count = 0
        total_positions = len(items)

        for item in items:
            price = item.product.price if item.product else 0.0
            total_amount += price * item.quantity
            total_count += item.quantity

        return items, total_amount, total_count, total_positions

    async def add_item(self, user_id: int, product_id: int, quantity: int) -> CartItem:
        return await self.repo.add_or_update_item(user_id, product_id, quantity)

    async def update_quantity(self, user_id: int, product_id: int, quantity: int) -> CartItem | None:
        return await self.repo.set_item_quantity(user_id, product_id, quantity)

    async def remove_item(self, user_id: int, product_id: int) -> bool:
        return await self.repo.remove_item(user_id, product_id)

    async def clear_cart(self, user_id: int) -> None:
        await self.repo.clear_cart(user_id)
