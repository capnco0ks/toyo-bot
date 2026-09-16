from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.category_repo import CategoryRepository
from app.database.models import Product, Category


class ProductService:
    def __init__(self, session: AsyncSession):
        self.product_repo = ProductRepository(session)
        self.category_repo = CategoryRepository(session)

    async def get_active_categories(self) -> List[Category]:
        return await self.category_repo.get_all_active()

    async def get_all_categories(self) -> List[Category]:
        return await self.category_repo.get_all()

    async def get_category_by_id(self, category_id: int) -> Optional[Category]:
        return await self.category_repo.get_by_id(category_id)

    async def get_products_by_category(
        self,
        category_id: int,
        only_active: bool = True,
        page: int = 1,
        page_size: int = 6,
    ) -> Tuple[List[Product], int, int]:
        """
        Returns (products, total_count, total_pages)
        """
        offset = (page - 1) * page_size
        products = await self.product_repo.get_by_category(
            category_id=category_id,
            only_active=only_active,
            limit=page_size,
            offset=offset,
        )
        total_count = await self.product_repo.count_by_category(
            category_id=category_id,
            only_active=only_active,
        )
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        return products, total_count, total_pages

    async def get_product_by_id(self, product_id: int) -> Optional[Product]:
        return await self.product_repo.get_by_id(product_id)

    async def search_products(
        self,
        query: str,
        only_active: bool = True,
        page: int = 1,
        page_size: int = 6,
    ) -> Tuple[List[Product], int, int]:
        offset = (page - 1) * page_size
        products = await self.product_repo.search(
            query=query,
            only_active=only_active,
            limit=page_size,
            offset=offset,
        )
        total_count = await self.product_repo.count_search(
            query=query,
            only_active=only_active,
        )
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        return products, total_count, total_pages

    async def update_price(self, product_id: int, new_price: float) -> Optional[Product]:
        return await self.product_repo.update_price(product_id, new_price)

    async def toggle_active(self, product_id: int) -> Optional[Product]:
        return await self.product_repo.toggle_active(product_id)

    async def delete_product(self, product_id: int) -> bool:
        return await self.product_repo.delete_or_deactivate(product_id)

    async def create_product(
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
    ) -> Product:
        return await self.product_repo.create(
            category_id=category_id,
            name=name,
            price=price,
            article=article,
            viscosity=viscosity,
            volume=volume,
            package=package,
            description=description,
            photo_file_id=photo_file_id,
        )
