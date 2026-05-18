def format_inventory_answer_fast(question: str, products: List[dict], lang: str) -> str:
    """
    Fast inventory formatter.
    Does not call the LLM.
    Used for low-latency catalog responses.
    """
    if not products:
        if lang == "ar":
            return "عذراً، لا يوجد منتجات مطابقة حالياً في الكتالوج."
        return "Sorry, I could not find matching products in the catalog."

    lines = []

    if lang == "ar":
        lines.append("المنتجات المتوفرة في الكتالوج:")
    else:
        lines.append("Here are the matching products:")

    for i, p in enumerate(products[:10], start=1):
        name = p.get("name") or "Unnamed product"
        sku = p.get("default_code") or ""
        price = p.get("sales_price", 0)
        qty = p.get("quantity_on_hand", 0)
        in_stock = bool(p.get("in_stock"))

        if lang == "ar":
            status = "متوفر" if in_stock else "غير متوفر"
            line = f"{i}. {name}"
            if sku:
                line += f" - SKU: {sku}"
            line += f" - السعر: {price} - الكمية: {qty} - الحالة: {status}"
        else:
            status = "IN STOCK" if in_stock else "OUT OF STOCK"
            line = f"{i}. {name}"
            if sku:
                line += f" - SKU: {sku}"
            line += f" - Price: {price} - Quantity: {qty} - {status}"

        lines.append(line)

    return "\n".join(lines)
