from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.order_repo import OrderRepository
from app.database.models import Order


class OrderService:
    def __init__(self, session: AsyncSession):
        self.repo = OrderRepository(session)

    async def create_order(self, user_id: int) -> Optional[Order]:
        return await self.repo.create_order_from_cart(user_id)

    async def get_order_by_id(self, order_id: int) -> Optional[Order]:
        return await self.repo.get_order_by_id(order_id)

    async def get_user_orders(
        self, user_id: int, page: int = 1, page_size: int = 5
    ) -> Tuple[List[Order], int, int]:
        offset = (page - 1) * page_size
        orders = await self.repo.get_user_orders(user_id, limit=page_size, offset=offset)
        total_count = await self.repo.count_user_orders(user_id)
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        return orders, total_count, total_pages

    async def update_order_status(self, order_id: int, status: str) -> Optional[Order]:
        return await self.repo.update_status(order_id, status)

    async def get_stats(self) -> Dict[str, Any]:
        return await self.repo.get_stats()
