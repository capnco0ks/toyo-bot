import os
import sys
import pytest
import pytest_asyncio
import asyncio

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database.models import Base, User, Category, Product, CartItem, Order, OrderItem
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.category_repo import CategoryRepository
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.cart_repo import CartRepository
from app.database.repositories.order_repo import OrderRepository
from app.services.cart_service import CartService
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.utils.formatters import format_currency, format_status, format_profile_text, format_delivery_data_preview


@pytest_asyncio.fixture
async def test_session():
    # In-memory SQLite database for fast, isolated tests
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_user_creation(test_session: AsyncSession):
    user_repo = UserRepository(test_session)
    user = await user_repo.get_or_create(
        telegram_id=111222333,
        username="john_doe",
        first_name="John",
        last_name="Doe",
    )
    assert user.id is not None
    assert user.telegram_id == 111222333
    assert user.full_name == "John Doe"

    # Second call returns existing
    user2 = await user_repo.get_or_create(telegram_id=111222333)
    assert user2.id == user.id


@pytest.mark.asyncio
async def test_catalog_and_search(test_session: AsyncSession):
    cat_repo = CategoryRepository(test_session)
    cat_motor = await cat_repo.create_category("Моторные масла", sort_order=1)
    cat_trans = await cat_repo.create_category("Трансмиссионные масла", sort_order=2)

    prod_repo = ProductRepository(test_session)
    p1 = await prod_repo.create(
        category_id=cat_motor.id,
        name="TOYO 5W30",
        price=13400.0,
        viscosity="5W30",
        volume="4 л",
        package="Металлическая канистра",
    )
    p2 = await prod_repo.create(
        category_id=cat_trans.id,
        name="TOYO ATF CVT",
        price=14500.0,
        volume="4 л",
        package="Металлическая канистра",
    )

    prod_service = ProductService(test_session)
    prods, total, _ = await prod_service.get_products_by_category(cat_motor.id)
    assert total == 1
    assert prods[0].name == "TOYO 5W30"

    # Search by viscosity
    res_visc, cnt, _ = await prod_service.search_products("5w30")
    assert cnt == 1
    assert res_visc[0].id == p1.id

    # Search by transmission spec
    res_atf, cnt2, _ = await prod_service.search_products("CVT")
    assert cnt2 == 1
    assert res_atf[0].id == p2.id


@pytest.mark.asyncio
async def test_cart_operations_and_calculations(test_session: AsyncSession):
    user_repo = UserRepository(test_session)
    user = await user_repo.get_or_create(telegram_id=100)

    cat_repo = CategoryRepository(test_session)
    cat = await cat_repo.create_category("Моторные масла")

    prod_repo = ProductRepository(test_session)
    p1 = await prod_repo.create(category_id=cat.id, name="Oil A", price=8500.0, volume="4 л")
    p2 = await prod_repo.create(category_id=cat.id, name="Oil B", price=9000.0, volume="4 л")
    p3 = await prod_repo.create(category_id=cat.id, name="Oil C", price=3000.0, volume="1 л")

    cart_service = CartService(test_session)

    # 10 x Oil A = 85 000
    await cart_service.add_item(user.id, p1.id, 10)
    # 5 x Oil B = 45 000
    await cart_service.add_item(user.id, p2.id, 5)
    # 20 x Oil C = 60 000
    await cart_service.add_item(user.id, p3.id, 20)

    items, total_amount, total_count, total_positions = await cart_service.get_cart_summary(user.id)
    assert total_positions == 3
    assert total_count == 35  # 10 + 5 + 20
    assert total_amount == 190000.0  # 85000 + 45000 + 60000

    # Modify quantity
    await cart_service.update_quantity(user.id, p2.id, 10)
    _, total_amount2, total_count2, _ = await cart_service.get_cart_summary(user.id)
    assert total_count2 == 40
    assert total_amount2 == 235000.0

    # Remove item
    await cart_service.remove_item(user.id, p3.id)
    items3, total_amount3, total_count3, total_positions3 = await cart_service.get_cart_summary(user.id)
    assert total_positions3 == 2
    assert total_count3 == 20


@pytest.mark.asyncio
async def test_order_creation_and_strict_price_freezing(test_session: AsyncSession):
    user_repo = UserRepository(test_session)
    user = await user_repo.get_or_create(telegram_id=200)
    await user_repo.update_profile(
        user.id, "Иван Иванов", "ТОО Тест", "+77011234567", "Астана", "ул. Абая, 1"
    )

    cat_repo = CategoryRepository(test_session)
    cat = await cat_repo.create_category("Моторные масла")

    prod_repo = ProductRepository(test_session)
    product = await prod_repo.create(category_id=cat.id, name="TOYO 5W-30 4L", price=8500.0)

    cart_service = CartService(test_session)
    await cart_service.add_item(user.id, product.id, 10)

    order_service = OrderService(test_session)
    order = await order_service.create_order(user.id)
    assert order is not None
    assert order.total_amount == 85000.0
    assert order.status == "new"
    assert len(order.items) == 1
    assert order.items[0].price_at_purchase == 8500.0
    assert order.items[0].total == 85000.0
    assert order.customer_name == "Иван Иванов"
    assert order.city == "Астана"
    assert order.delivery_address == "ул. Абая, 1"

    # Cart must be cleared after order
    items_after, _, _, _ = await cart_service.get_cart_summary(user.id)
    assert len(items_after) == 0

    # ADMIN changes product price from 8 500 to 9 000
    prod_service = ProductService(test_session)
    await prod_service.update_price(product.id, 9000.0)

    # Verify past order REMAINS 8 500
    saved_order = await order_service.get_order_by_id(order.id)
    assert saved_order.items[0].price_at_purchase == 8500.0
    assert saved_order.total_amount == 85000.0

    # New order gets new price 9 000
    await cart_service.add_item(user.id, product.id, 5)
    order2 = await order_service.create_order(user.id)
    assert order2.items[0].price_at_purchase == 9000.0
    assert order2.total_amount == 45000.0


@pytest.mark.asyncio
async def test_scenario_1_and_2_profile_flow_and_auto_reuse(test_session: AsyncSession):
    """
    Scenario 1: New user fills profile -> creates order with delivery data.
    Scenario 2: Existing user profile is auto-reused without re-prompting.
    """
    user_repo = UserRepository(test_session)
    user = await user_repo.get_or_create(telegram_id=500, first_name="Алибек")
    assert user.is_profile_complete() is False

    # Fill profile
    await user_repo.update_profile(
        user_id=user.id,
        full_name="Алибек Сериков",
        company_name="ТОО АвтоМасла",
        phone="+7 777 000 11 22",
        city="Алматы",
        delivery_address="ул. Толе би, 50, склад 3",
    )
    user_updated = await user_repo.get_by_id(user.id)
    assert user_updated.is_profile_complete() is True

    cat_repo = CategoryRepository(test_session)
    cat = await cat_repo.create_category("Моторные масла")
    prod_repo = ProductRepository(test_session)
    p = await prod_repo.create(category_id=cat.id, name="TOYO 5W-40 4L", price=13400.0)

    cart_service = CartService(test_session)
    await cart_service.add_item(user.id, p.id, 2)

    order_service = OrderService(test_session)
    order1 = await order_service.create_order(user.id)
    assert order1.customer_name == "Алибек Сериков"
    assert order1.company_name == "ТОО АвтоМасла"
    assert order1.phone == "+7 777 000 11 22"
    assert order1.city == "Алматы"
    assert order1.delivery_address == "ул. Толе би, 50, склад 3"
    assert order1.total_amount == 26800.0

    # Scenario 2: Next order auto-uses profile
    await cart_service.add_item(user.id, p.id, 1)
    order2 = await order_service.create_order(user.id)
    assert order2.customer_name == "Алибек Сериков"
    assert order2.delivery_address == "ул. Толе би, 50, склад 3"


@pytest.mark.asyncio
async def test_scenario_3_and_4_address_and_phone_immutability(test_session: AsyncSession):
    """
    Scenario 3: User changes address -> new order has new address, old order retains old address.
    Scenario 4: User changes phone -> old orders keep old phone.
    """
    user_repo = UserRepository(test_session)
    user = await user_repo.get_or_create(telegram_id=600)
    await user_repo.update_profile(
        user.id, "Диас", "ТОО Старт", "+7 705 111 22 33", "Астана", "Старый адрес 1"
    )

    cat_repo = CategoryRepository(test_session)
    cat = await cat_repo.create_category("Трансмиссионные масла")
    prod_repo = ProductRepository(test_session)
    p = await prod_repo.create(category_id=cat.id, name="TOYO ATF WS", price=15000.0)

    cart_service = CartService(test_session)
    await cart_service.add_item(user.id, p.id, 3)

    order_service = OrderService(test_session)
    order1 = await order_service.create_order(user.id)
    assert order1.delivery_address == "Старый адрес 1"
    assert order1.phone == "+7 705 111 22 33"

    # User changes address and phone in profile
    await user_repo.update_field(user.id, "address", "Новый адрес 99, бокс 5")
    await user_repo.update_field(user.id, "phone", "+7 777 999 88 77")

    # New order
    await cart_service.add_item(user.id, p.id, 1)
    order2 = await order_service.create_order(user.id)

    # Check that old order retains historical data!
    o1_fetched = await order_service.get_order_by_id(order1.id)
    assert o1_fetched.delivery_address == "Старый адрес 1"
    assert o1_fetched.phone == "+7 705 111 22 33"

    # Check new order has new data
    assert order2.delivery_address == "Новый адрес 99, бокс 5"
    assert order2.phone == "+7 777 999 88 77"


@pytest.mark.asyncio
async def test_scenario_6_data_isolation_between_users(test_session: AsyncSession):
    """
    Scenario 6: Two different users cannot access or overwrite each other's carts or orders.
    """
    user_repo = UserRepository(test_session)
    u1 = await user_repo.get_or_create(telegram_id=701)
    await user_repo.update_profile(u1.id, "Пользователь 1", "Компани 1", "+7 111", "Астана", "Адрес 1")

    u2 = await user_repo.get_or_create(telegram_id=702)
    await user_repo.update_profile(u2.id, "Пользователь 2", "Компани 2", "+7 222", "Алматы", "Адрес 2")

    cat_repo = CategoryRepository(test_session)
    cat = await cat_repo.create_category("Масла")
    prod_repo = ProductRepository(test_session)
    p = await prod_repo.create(category_id=cat.id, name="Oil X", price=5000.0)

    cart_service = CartService(test_session)
    await cart_service.add_item(u1.id, p.id, 2)
    await cart_service.add_item(u2.id, p.id, 10)

    items1, amt1, cnt1, _ = await cart_service.get_cart_summary(u1.id)
    items2, amt2, cnt2, _ = await cart_service.get_cart_summary(u2.id)

    assert cnt1 == 2
    assert amt1 == 10000.0
    assert cnt2 == 10
    assert amt2 == 50000.0

    order_service = OrderService(test_session)
    o1 = await order_service.create_order(u1.id)
    o2 = await order_service.create_order(u2.id)

    u1_orders, cnt_o1, _ = await order_service.get_user_orders(u1.id)
    assert cnt_o1 == 1
    assert u1_orders[0].id == o1.id
    assert u1_orders[0].customer_name == "Пользователь 1"

    u2_orders, cnt_o2, _ = await order_service.get_user_orders(u2.id)
    assert cnt_o2 == 1
    assert u2_orders[0].id == o2.id
    assert u2_orders[0].customer_name == "Пользователь 2"


@pytest.mark.asyncio
async def test_order_status_workflow(test_session: AsyncSession):
    user_repo = UserRepository(test_session)
    user = await user_repo.get_or_create(telegram_id=300)

    cat_repo = CategoryRepository(test_session)
    cat = await cat_repo.create_category("Моторные масла")
    prod_repo = ProductRepository(test_session)
    p = await prod_repo.create(category_id=cat.id, name="Oil Test", price=10000.0)

    cart_service = CartService(test_session)
    await cart_service.add_item(user.id, p.id, 2)

    order_service = OrderService(test_session)
    order = await order_service.create_order(user.id)
    assert order.status == "new"

    # Manager accepts order
    await order_service.update_order_status(
        order.id, "accepted", accepted_by_id=777888, accepted_by_name="@alex_manager"
    )
    o_accepted = await order_service.get_order_by_id(order.id)
    assert o_accepted.status == "accepted"
    assert o_accepted.accepted_by_id == 777888
    assert o_accepted.accepted_by_name == "@alex_manager"

    # Manager completes order
    await order_service.update_order_status(order.id, "completed")
    o_comp = await order_service.get_order_by_id(order.id)
    assert o_comp.status == "completed"
    assert o_comp.accepted_by_id == 777888


@pytest.mark.asyncio
async def test_product_deactivation_preserves_orders(test_session: AsyncSession):
    user_repo = UserRepository(test_session)
    user = await user_repo.get_or_create(telegram_id=400)

    cat_repo = CategoryRepository(test_session)
    cat = await cat_repo.create_category("Категория")
    prod_repo = ProductRepository(test_session)
    p = await prod_repo.create(category_id=cat.id, name="Rare Oil", price=25000.0)

    cart_service = CartService(test_session)
    await cart_service.add_item(user.id, p.id, 1)

    order_service = OrderService(test_session)
    order = await order_service.create_order(user.id)

    # Deactivate / delete product
    prod_service = ProductService(test_session)
    await prod_service.delete_product(p.id)

    # Product is deactivated because orders exist
    p_updated = await prod_service.get_product_by_id(p.id)
    assert p_updated.is_active is False

    # Historical order intact
    saved_order = await order_service.get_order_by_id(order.id)
    assert saved_order is not None
    assert saved_order.items[0].product_name == "Rare Oil"
    assert saved_order.items[0].price_at_purchase == 25000.0


def test_formatters():
    assert format_currency(190000) == "190 000 ₸"
    assert format_currency(8500.0) == "8 500 ₸"
    assert "НОВЫЙ" in format_status("new")
    assert "ПРИНЯТ" in format_status("accepted")

    from app.database.models import Product
    prod = Product(name="TOYO 5W-30", volume="4 л", package="металл", price=12500)
    assert prod.full_title == "TOYO 5W-30 4 л (металл)"

