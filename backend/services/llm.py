"""
LLM Service — system prompts, chat completions, response formatting.
Handles RAG answers, inventory answers (with product reasoning), and smalltalk.
"""

from typing import List
from config import openai_client, LLM_MODEL
from utils import detect_lang, format_now, now_in_lebanon
from services import odoo


def build_system_prompt(lang: str) -> str:
    now_str = format_now(now_in_lebanon())
    return f"""You are an AI Receptionist and Customer Support Assistant for Axion.
CAPABILITIES:
1. Product catalog with live-synced prices and stock levels.
2. PDF Knowledge Base from Supabase RAG.
3. Voice and text support.
RESPONSE RULES:
- Answer in the user's language, Arabic or English.
- Be accurate, brief, and professional.
- Do not invent stock or price.
- Current date/time: {now_str}
"""


def _format_products(products: List[dict]) -> str:
    if not products:
        return "(no matching products found in catalog)"
    lines = []
    for p in products:
        line = f"- {p.get('name', '')}"
        code = p.get("default_code", "")
        if code:
            line += f" (SKU: {code})"
        cat = p.get("category_name", "")
        if cat:
            line += f" [{cat}]"
        qty = p.get("quantity_on_hand", 0)
        price = p.get("sales_price", 0)
        status = "IN STOCK" if p.get("in_stock") else "OUT OF STOCK"
        line += f" | Price: {price} | Stock: {qty} | {status}"
        lines.append(line)
    return "\n".join(lines)


def generate_rag_answer(question: str, pdf_context: str, lang: str, history: List[dict] = None) -> str:
    system_prompt = build_system_prompt(lang)
    user_prompt = f"PDF Context:\n{pdf_context}\n\nUser question:\n{question}"
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_prompt})
    try:
        resp = openai_client.chat.completions.create(model=LLM_MODEL, temperature=0, max_tokens=500, messages=messages)
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"LLM error: {type(e).__name__}: {e}"


def generate_inventory_answer(question: str, products: List[dict], lang: str, history: List[dict] = None) -> str:
    product_context = _format_products(products)
    lang_instruction = "Answer in Arabic." if lang == "ar" else "Answer in English."
    system_prompt = f"""You are Axion's AI sales assistant. {lang_instruction}
Use ONLY this product data to answer. Never invent products or prices.
Be concise. Always mention price and stock status.
Remember conversation context.

PRODUCTS:
{product_context}"""
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})
    try:
        resp = openai_client.chat.completions.create(model=LLM_MODEL, temperature=0.1, max_tokens=500, messages=messages)
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"LLM error: {type(e).__name__}: {e}"


def format_smalltalk(lang: str) -> str:
    return "Hello! How can I assist you today?" if lang == "en" else "مرحباً! كيف يمكنني مساعدتك اليوم؟"


def append_sources(answer: str, pages: List[int], lang: str) -> str:
    if not pages:
        return answer
    page_str = ", ".join(str(p) for p in pages)
    if lang == "en":
        return answer + f"\n\nSources (pages): {page_str}"
    return answer + f"\n\nالمصادر (الصفحات): {page_str}"
