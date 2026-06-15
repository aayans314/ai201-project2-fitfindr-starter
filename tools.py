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
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)

# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """Search the mock listings dataset for matching items."""
    all_listings = load_listings()
    filtered_listings = []
    
    # Extract keywords from description for scoring
    desc_words = set(re.findall(r'\w+', description.lower()))
    
    for item in all_listings:
        # Filter by price
        if max_price is not None and item.get("price", float('inf')) > max_price:
            continue
            
        # Filter by size (case-insensitive substring match)
        if size is not None:
            item_size = str(item.get("size", "")).lower()
            if size.lower() not in item_size:
                continue
                
        # Calculate relevance score based on keyword overlap
        item_text = f"{item.get('title', '')} {item.get('description', '')} {' '.join(item.get('style_tags', []))}".lower()
        item_words = set(re.findall(r'\w+', item_text))
        
        score = len(desc_words.intersection(item_words))
        
        if score > 0:
            item_copy = item.copy()
            item_copy["_score"] = score
            filtered_listings.append(item_copy)
            
    # Sort by score descending
    filtered_listings.sort(key=lambda x: x["_score"], reverse=True)
    
    # Clean up temporary score key
    for item in filtered_listings:
        del item["_score"]
        
    return filtered_listings

# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """Suggest complete outfits using a thrifted item and the user's wardrobe."""
    client = _get_groq_client()
    items = wardrobe.get("items", [])
    
    item_str = f"{new_item.get('title')} ({new_item.get('category')})"
    
    if not items:
        # Fallback: empty wardrobe
        prompt = (
            f"The user is considering buying a '{item_str}'. Their wardrobe is currently empty. "
            f"Provide 1-2 paragraphs of general styling advice on how to wear this item, "
            f"what kinds of pieces pair well with it, and the overall vibe."
        )
    else:
        # Standard: use existing wardrobe
        wardrobe_str = "\n".join([f"- {w.get('name')} ({w.get('category')})" for w in items])
        prompt = (
            f"The user is considering buying a '{item_str}'. Here is their current wardrobe:\n{wardrobe_str}\n\n"
            f"Suggest 1-2 complete outfit combinations using the new item and ONLY pieces "
            f"from their current wardrobe. Be specific about why the pieces work together."
        )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500
    )
    
    return response.choices[0].message.content.strip()

# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """Generate a short, shareable outfit caption."""
    if not outfit or not outfit.strip():
        return "Error: Missing outfit data to generate a fit card."
        
    client = _get_groq_client()
    
    prompt = (
        f"Item details: {new_item.get('title')} for ${new_item.get('price')} on {new_item.get('platform')}.\n"
        f"Outfit vibe: {outfit}\n\n"
        f"Write a 2-4 sentence caption for an Instagram or TikTok post. "
        f"Feel casual and authentic (lower case is fine). Mention the item name, price, and platform naturally. "
        f"Do NOT use hashtags. Do NOT add quotation marks."
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9, # Higher temp for variance
        max_tokens=150
    )
    
    return response.choices[0].message.content.strip()