import json
from tools import _get_groq_client, search_listings, suggest_outfit, create_fit_card, compare_price, get_trending_styles

def _new_session(query: str, wardrobe: dict, style_memory: str) -> dict:
    return {
        "query": query, "parsed": {}, "search_results": [],
        "selected_item": None, "wardrobe": wardrobe,
        "price_assessment": None, "trends": None,
        "outfit_suggestion": None, "fit_card": None,
        "style_memory": style_memory, "retry_message": None, "error": None,
    }

def _parse_query(query: str) -> dict:
    client = _get_groq_client()
    prompt = (
        f"Extract search parameters from this query: '{query}'\n"
        f"Return ONLY a valid JSON object with: 'description' (string), 'size' (string or null), 'max_price' (float or null)."
    )
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    try:
        content = response.choices[0].message.content.strip()
        # Fixed string check to prevent markdown parsers from breaking
        if content.startswith("```" + "json"): 
            content = content[7:-3]
        return json.loads(content)
    except json.JSONDecodeError:
        return {"description": query, "size": None, "max_price": None}

def run_agent(query: str, wardrobe: dict, style_memory: str = "") -> dict:
    # Append current query to style memory for persistent profile
    updated_memory = f"{style_memory} | User requested: {query}" if style_memory else f"User requested: {query}"
    session = _new_session(query, wardrobe, updated_memory)
    session["parsed"] = _parse_query(query)
    
    # Tool 1: Search
    session["search_results"] = search_listings(
        description=session["parsed"].get("description", query),
        size=session["parsed"].get("size"),
        max_price=session["parsed"].get("max_price")
    )
    
    # STRETCH: Retry Logic with Fallback
    if not session["search_results"] and (session["parsed"].get("size") or session["parsed"].get("max_price")):
        session["retry_message"] = "⚠️ No exact matches found. We removed your size/price filters to find similar items!"
        session["search_results"] = search_listings(description=session["parsed"].get("description", query))
        
    if not session["search_results"]:
        session["error"] = "No matching items found, even after expanding the search. Please try a different item."
        return session
        
    session["selected_item"] = session["search_results"][0]
    
    # Tool 4 (Stretch): Price Comparison
    session["price_assessment"] = compare_price(session["selected_item"])
    
    # Tool 5 (Stretch): Trend Awareness
    session["trends"] = get_trending_styles(session["parsed"].get("size"))
    
    # Tool 2: Suggest Outfit (Now uses Memory and Trends)
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"], session["wardrobe"], 
        session["trends"], session["style_memory"]
    )
    
    # Tool 3: Fit Card
    session["fit_card"] = create_fit_card(session["outfit_suggestion"], session["selected_item"])
    return session