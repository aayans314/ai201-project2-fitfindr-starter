import os
import json
import re
from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()

# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to a .env file in the project root.")
    return Groq(api_key=api_key)

# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(description: str, size: str | None = None, max_price: float | None = None) -> list[dict]:
    """Search the mock listings dataset for matching items."""
    all_listings = load_listings()
    filtered_listings = []
    desc_words = set(re.findall(r'\w+', description.lower()))
    
    for item in all_listings:
        if max_price is not None and item.get("price", float('inf')) > max_price: continue
        if size is not None:
            item_size = str(item.get("size", "")).lower()
            if size.lower() not in item_size: continue
                
        item_text = f"{item.get('title', '')} {item.get('description', '')} {' '.join(item.get('style_tags', []))}".lower()
        item_words = set(re.findall(r'\w+', item_text))
        score = len(desc_words.intersection(item_words))
        
        if score > 0:
            item_copy = item.copy()
            item_copy["_score"] = score
            filtered_listings.append(item_copy)
            
    filtered_listings.sort(key=lambda x: x["_score"], reverse=True)
    for item in filtered_listings: del item["_score"]
    return filtered_listings

# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict, trends: str = "", style_memory: str = "") -> str:
    """Suggest complete outfits using a thrifted item, the user's wardrobe, and trends."""
    client = _get_groq_client()
    items = wardrobe.get("items", [])
    item_str = f"{new_item.get('title')} ({new_item.get('category')})"
    
    context = ""
    if trends: context += f"Current fashion trends: {trends}\n"
    if style_memory: context += f"User's past style preferences: {style_memory}\n"
    
    if not items:
        prompt = (
            f"{context}\nThe user is considering buying a '{item_str}'. Their wardrobe is currently empty. "
            f"Provide 1-2 paragraphs of general styling advice on how to wear this item. "
            f"Explicitly weave in the trend information and their past style preferences if available."
        )
    else:
        wardrobe_str = "\n".join([f"- {w.get('name')} ({w.get('category')})" for w in items])
        prompt = (
            f"{context}\nThe user is considering buying a '{item_str}'. Here is their current wardrobe:\n{wardrobe_str}\n\n"
            f"Suggest 1-2 complete outfit combinations using the new item and ONLY pieces from their current wardrobe. "
            f"Explicitly mention how the outfit aligns with current trends and their past preferences."
        )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7, max_tokens=500
    )
    return response.choices[0].message.content.strip()

# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """Generate a short, shareable outfit caption."""
    if not outfit or not outfit.strip(): return "Error: Missing outfit data to generate a fit card."
    client = _get_groq_client()
    prompt = (
        f"Item details: {new_item.get('title')} for ${new_item.get('price')} on {new_item.get('platform')}.\n"
        f"Outfit vibe: {outfit}\n\n"
        f"Write a 2-4 sentence caption for an Instagram or TikTok post. Feel casual and authentic. "
        f"Mention the item name, price, and platform naturally. Do NOT use hashtags or quotes."
    )
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9, max_tokens=150
    )
    return response.choices[0].message.content.strip()

# ── Tool 4: compare_price (Stretch) ───────────────────────────────────────────

def compare_price(new_item: dict) -> str:
    """Compare an item's price against similar items in the mock dataset."""
    all_listings = load_listings()
    category = new_item.get("category")
    similar_items = [item for item in all_listings if item.get("category") == category and item.get("id") != new_item.get("id")]
    
    if not similar_items: return "No comparable items found to assess price."
    
    avg_price = sum(item.get("price", 0) for item in similar_items) / len(similar_items)
    item_price = new_item.get("price", 0)
    
    if item_price < avg_price:
        return f"Great deal! At ${item_price:.2f}, this is below the category average of ${avg_price:.2f}."
    return f"Fair price. This is ${item_price:.2f}, compared to the average of ${avg_price:.2f} for {category}."

# ── Tool 5: get_trending_styles (Stretch) ─────────────────────────────────────

def get_trending_styles(size: str | None = None) -> str:
    """Check recent fashion trends via LLM to influence outfit suggestions."""
    client = _get_groq_client()
    size_context = f" for size {size}" if size else ""
    prompt = (
        f"Briefly summarize 2 current streetwear or thrift fashion trends{size_context}. "
        f"Keep it under 3 sentences. Focus on silhouettes, aesthetics, or specific combinations."
    )
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7, max_tokens=100
    )
    return response.choices[0].message.content.strip()