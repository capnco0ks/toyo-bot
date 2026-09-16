from typing import Optional
from aiogram.filters.callback_data import CallbackData


class CategoryCallback(CallbackData, prefix="c"):
    category_id: int
    page: int = 1


class ProductCallback(CallbackData, prefix="p"):
    product_id: int
    category_id: int = 0
    page: int = 1


class ProductQuantityCallback(CallbackData, prefix="q"):
    product_id: int
    quantity: int
    category_id: int = 0
    page: int = 1


class AddToCartCallback(CallbackData, prefix="ac"):
    product_id: int
    quantity: int
    category_id: int = 0
    page: int = 1


class CartItemCallback(CallbackData, prefix="ci"):
    product_id: int


class CartItemQtyCallback(CallbackData, prefix="cq"):
    product_id: int
    quantity: int


class CartActionCallback(CallbackData, prefix="ca"):
    action: str  # view, edit, clear, checkout, confirm


class OrderDetailCallback(CallbackData, prefix="od"):
    order_id: int
    page: int = 1


class ManagerOrderActionCallback(CallbackData, prefix="mo"):
    order_id: int
    action: str  # accept, reject, complete


class AdminProductCallback(CallbackData, prefix="ap"):
    product_id: int
    action: str  # view, toggle, edit_price, delete, choose_cat
    category_id: int = 0
    page: int = 1


class AdminCategoryCallback(CallbackData, prefix="ac_adm"):
    category_id: int
    action: str  # view, add_product_to, edit_price_in
    page: int = 1


class AdminMenuCallback(CallbackData, prefix="adm"):
    menu: str  # main, products, add_product, edit_price, stats


class ProfileCallback(CallbackData, prefix="prf"):
    action: str  # view, edit, edit_field
    field: Optional[str] = None  # name, company, phone, city, address


class CheckoutDataCallback(CallbackData, prefix="chk"):
    action: str  # confirm_data, edit_data, edit_field
    field: Optional[str] = None  # name, company, phone, city, address
