"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""
import json
from tools import _get_groq_client, search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── helper ────────────────────────────────────────────────────────────────────
def _parse_query(query: str) -> dict:
    """Uses LLM to extract search parameters from natural language."""
    client = _get_groq_client()
    prompt = (
        f"Extract search parameters from this query: '{query}'\n"
        f"Return ONLY a valid JSON object with these exactly keys: \n"
        f"'description' (string, the main item being sought),\n"
        f"'size' (string or null),\n"
        f"'max_price' (float or null).\n"
        f"Do not include markdown blocks or any other text."
    )
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    
    try:
        content = response.choices[0].message.content.strip()
        # Clean up potential markdown formatting from LLM
        if content.startswith("```json"):
            content = content[7:-3]
        return json.loads(content)
    except json.JSONDecodeError:
        # Fallback if LLM fails to return valid JSON
        return {"description": query, "size": None, "max_price": None}

# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """Main agent entry point. Orchestrates the tools."""
    # Step 1
    session = _new_session(query, wardrobe)
    
    # Step 2
    session["parsed"] = _parse_query(query)
    
    # Step 3
    session["search_results"] = search_listings(
        description=session["parsed"].get("description", query),
        size=session["parsed"].get("size"),
        max_price=session["parsed"].get("max_price")
    )
    
    # Step 4 (Condition A - Failure mode branch)
    if not session["search_results"]:
        session["error"] = "No matching items found in the listings. Please try with a different choice!"
        return session
        
    # Step 5 (Condition B - Success branch)
    session["selected_item"] = session["search_results"][0]
    
    # Step 6
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"], 
        session["wardrobe"]
    )
    
    # Step 7
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"], 
        session["selected_item"]
    )
    
    # Step 8
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
    print(f"Whats in fit card?: {session2['fit_card']}")
