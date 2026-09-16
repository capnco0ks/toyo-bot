import asyncio
import os
import re
import sys
from typing import Optional, Tuple
import xlrd
from sqlalchemy import select

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.database.database import get_engine, init_db, async_session_factory
from app.database.models import Category, Product


def parse_oil_row(col0: str, col1: str, col2: float) -> dict:
    raw_col0 = str(col0).strip()
    raw_col1 = str(col1).strip()
    price = float(col2)

    # 1. Category
    if "моторное" in raw_col0.lower():
        category_name = "Моторные масла"
        cat_sort = 1
    elif "трансмиссионное" in raw_col0.lower():
        category_name = "Трансмиссионные масла"
        cat_sort = 2
    else:
        category_name = "Масла TOYO"
        cat_sort = 3

    # 2. Volume extraction from (1), (4), (5), (20), (208)
    vol_match = re.search(r"\((\d+)\)", raw_col0) or re.search(r"\((\d+)\)", raw_col1)
    vol_num = int(vol_match.group(1)) if vol_match else None
    if vol_num == 208:
        volume = "208 л (бочка)"
    elif vol_num:
        volume = f"{vol_num} л"
    else:
        volume = None

    # 3. Package
    combined = f"{raw_col0} {raw_col1}".lower()
    if vol_num == 208:
        package = "Металлическая бочка"
    elif "метал" in combined:
        package = "Металлическая канистра"
    elif "пластик" in combined:
        package = "Пластиковая канистра"
    else:
        package = "Канистра"

    # 4. Viscosity
    visc_match = re.search(r"\b(\d{1,2}[wW]\d{2}|\d{2}[wW]\d{2})\b", f"{raw_col0} {raw_col1}")
    if visc_match:
        viscosity = visc_match.group(1).upper()
    else:
        viscosity = None

    # 5. Clean, Professional Product Name
    # Extract extra specs (DEXOS 2, MULTI GREEN, API SP, GL-5, ATF CVT, etc.)
    extra_specs = []
    if "dexos 2" in combined:
        extra_specs.append("DEXOS 2")
    if "multi green" in combined or " mg " in combined or "(mg)" in combined.replace(" ", ""):
        extra_specs.append("MULTI GREEN")
    if "api sp" in combined:
        extra_specs.append("API SP")
    if "gl-5" in combined:
        extra_specs.append("GL-5")

    # For transmission oils:
    atf_types = [
        ("dsg/dct", "DSG/DCT FLUID"),
        ("cvt", "ATF CVT"),
        ("dex vi", "ATF DEXRON VI"),
        ("t-iv", "ATF T-IV"),
        ("ws", "ATF WS"),
        ("hmmf", "ATF MULTI (HMMF)"),
        ("dexron iii", "ATF DEXRON III"),
        ("dex 3", "ATF DEXRON III"),
        ("sp-4", "ATF SP-4"),
        ("gear oil", "GEAR OIL"),
    ]

    for key, spec_title in atf_types:
        if key in combined:
            if spec_title not in extra_specs:
                extra_specs.append(spec_title)

    spec_str = " " + " ".join(extra_specs) if extra_specs else ""
    visc_str = f" {viscosity}" if viscosity else ""

    if category_name == "Моторные масла":
        product_name = f"TOYO{visc_str}{spec_str}".strip()
    else:
        # Transmission
        if extra_specs:
            spec_display = " ".join(extra_specs)
            product_name = f"TOYO {spec_display}{visc_str}".strip()
        else:
            product_name = f"TOYO{visc_str}".strip()

    # Article if applicable
    article = f"TOYO-{viscosity or 'OIL'}-{vol_num or '1'}"

    description = f"{raw_col0}\nКраткое наименование: {raw_col1}"

    return {
        "category_name": category_name,
        "category_sort": cat_sort,
        "name": product_name,
        "viscosity": viscosity,
        "volume": volume,
        "package": package,
        "price": price,
        "article": article,
        "description": description,
    }


async def import_products_from_excel(file_path: str) -> None:
    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        sys.exit(1)

    print(f"Reading price list from: {file_path}")
    wb = xlrd.open_workbook(file_path)
    sheet = wb.sheet_by_index(0)
    print(f"Sheet: {sheet.name} ({sheet.nrows} rows, {sheet.ncols} columns)")

    # Ensure DB schema is ready
    await init_db()

    imported_count = 0
    updated_count = 0

    async with async_session_factory() as session:
        # 1. Process categories cache
        categories_map = {}
        stmt = select(Category)
        res = await session.execute(stmt)
        for cat in res.scalars():
            categories_map[cat.name] = cat

        # 2. Iterate rows (skip header row 0)
        for row_idx in range(1, sheet.nrows):
            col0 = sheet.cell_value(row_idx, 0)
            col1 = sheet.cell_value(row_idx, 1)
            col2 = sheet.cell_value(row_idx, 2)

            if not col0 or not col2:
                continue

            parsed = parse_oil_row(col0, col1, col2)

            # Ensure category exists
            cat_name = parsed["category_name"]
            if cat_name not in categories_map:
                new_cat = Category(
                    name=cat_name,
                    sort_order=parsed["category_sort"],
                    is_active=True,
                )
                session.add(new_cat)
                await session.flush()
                categories_map[cat_name] = new_cat

            category = categories_map[cat_name]

            # Look for existing product with matching name, volume, package
            stmt = select(Product).where(
                Product.category_id == category.id,
                Product.name == parsed["name"],
                Product.volume == parsed["volume"],
                Product.package == parsed["package"],
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()

            if existing:
                if existing.price != parsed["price"]:
                    print(f"Updating price for {existing.name} ({existing.volume}): {existing.price} -> {parsed['price']} KZT")
                    existing.price = parsed["price"]
                    updated_count += 1
                existing.is_active = True
                existing.description = parsed["description"]
                existing.article = parsed["article"]
            else:
                new_prod = Product(
                    category_id=category.id,
                    name=parsed["name"],
                    price=parsed["price"],
                    viscosity=parsed["viscosity"],
                    volume=parsed["volume"],
                    package=parsed["package"],
                    article=parsed["article"],
                    description=parsed["description"],
                    is_active=True,
                )
                session.add(new_prod)
                imported_count += 1
                print(f"Added: [{cat_name}] {parsed['name']} ({parsed['volume']}, {parsed['package']}) - {parsed['price']:,.0f} KZT".replace(",", " "))

        await session.commit()

    print("\n" + "=" * 50)
    print("Import completed successfully!")
    print(f"Newly added products: {imported_count}")
    print(f"Updated products: {updated_count}")
    print("=" * 50)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    path = sys.argv[1] if len(sys.argv) > 1 else settings.DEFAULT_PRICE_PATH
    asyncio.run(import_products_from_excel(path))
