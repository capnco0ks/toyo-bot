from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Order, OrderItem, User, CartItem, Product


class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_order_from_cart(self, user_id: int) -> Optional[Order]:
        """
        Creates an order from the user's current cart.
        Freezes product prices into OrderItem.price_at_purchase.
        Snapshots customer profile and delivery address into Order.
        Clears user's cart upon success.
        """
        stmt = (
            select(CartItem)
            .options(selectinload(CartItem.product))
            .where(CartItem.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        cart_items = list(result.scalars().all())
        if not cart_items:
            return None

        # Fetch user profile to snapshot
        user_stmt = select(User).where(User.id == user_id)
        user = (await self.session.execute(user_stmt)).scalar_one_or_none()

        total_amount = 0.0
        order_items: List[OrderItem] = []

        for ci in cart_items:
            prod = ci.product
            # Check price snapshot
            price = prod.price if prod else 0.0
            prod_name = prod.name if prod else "Товар удален"
            item_total = price * ci.quantity
            total_amount += item_total

            order_item = OrderItem(
                product_id=prod.id if prod else None,
                product_name=prod_name,
                quantity=ci.quantity,
                price_at_purchase=price,
                total=item_total,
            )
            order_items.append(order_item)

        order = Order(
            user_id=user_id,
            total_amount=total_amount,
            status="new",
            customer_name=user.saved_full_name or user.display_name if user else "Клиент",
            company_name=user.company_name if user else None,
            phone=user.phone if user else "",
            city=user.city if user else "",
            delivery_address=user.delivery_address if user else "",
            items=order_items,
        )
        self.session.add(order)

        # Delete cart items
        for ci in cart_items:
            await self.session.delete(ci)

        await self.session.commit()
        return await self.get_order_by_id(order.id)

    async def get_order_by_id(self, order_id: int) -> Optional[Order]:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.user),
                selectinload(Order.items).selectinload(OrderItem.product),
            )
            .where(Order.id == order_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_orders(self, user_id: int, limit: int = 10, offset: int = 0) -> List[Order]:
        stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_user_orders(self, user_id: int) -> int:
        stmt = select(func.count(Order.id)).where(Order.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def update_status(self, order_id: int, status: str) -> Optional[Order]:
        order = await self.get_order_by_id(order_id)
        if order:
            order.status = status
            await self.session.commit()
            await self.session.refresh(order)
        return order

    async def get_stats(self) -> Dict[str, Any]:
        total_orders = await self.session.scalar(select(func.count(Order.id))) or 0
        total_revenue = await self.session.scalar(
            select(func.sum(Order.total_amount)).where(Order.status != "rejected")
        ) or 0.0
        new_orders = await self.session.scalar(
            select(func.count(Order.id)).where(Order.status == "new")
        ) or 0
        accepted_orders = await self.session.scalar(
            select(func.count(Order.id)).where(Order.status == "accepted")
        ) or 0
        total_users = await self.session.scalar(select(func.count(User.id))) or 0
        total_products = await self.session.scalar(
            select(func.count(Product.id)).where(Product.is_active.is_(True))
        ) or 0

        return {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "new_orders": new_orders,
            "accepted_orders": accepted_orders,
            "total_users": total_users,
            "total_products": total_products,
        }
