import pytest
from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

# ── Tests for Tool 1: search_listings ─────────────────────────────────────────

def test_search_returns_results():
    """Happy path: search returns valid list of dicts."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    """Failure mode: query matching nothing returns empty list, no exception."""
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []

def test_search_price_filter():
    """Edge case: max_price strictly filters results."""
    results = search_listings("jeans", size=None, max_price=20)
    assert all(item["price"] <= 20 for item in results)

def test_search_size_filter():
    """Edge case: size matching is case-insensitive and works as a substring."""
    # Assuming "M" matches "M" or "S/M" in the dataset
    results = search_listings("shirt", size="m", max_price=None)
    assert all("m" in str(item.get("size", "")).lower() for item in results)

def test_search_combined_filters():
    """Edge case: multiple filters applied together."""
    results = search_listings("jeans", size="30", max_price=40)
    for item in results:
        assert item["price"] <= 40
        assert "30" in str(item.get("size", "")).lower()


# ── Tests for Tool 2: suggest_outfit ──────────────────────────────────────────

def test_suggest_outfit_happy_path():
    """Happy path: generates outfit using a populated wardrobe."""
    new_item = {"title": "Vintage Levi's", "category": "bottoms"}
    wardrobe = get_example_wardrobe()
    result = suggest_outfit(new_item, wardrobe)
    
    assert isinstance(result, str)
    assert len(result) > 0

def test_suggest_outfit_empty_wardrobe():
    """Failure mode: handles empty wardrobe by offering general advice without crashing."""
    new_item = {"title": "Y2K Baby Tee", "category": "tops"}
    wardrobe = get_empty_wardrobe()
    result = suggest_outfit(new_item, wardrobe)
    
    assert isinstance(result, str)
    assert len(result) > 0

def test_suggest_outfit_missing_items_key():
    """Edge case: handles malformed wardrobe dictionary missing the 'items' key."""
    new_item = {"title": "Chunky Boots", "category": "shoes"}
    wardrobe = {} # Totally empty dict, no 'items' key
    result = suggest_outfit(new_item, wardrobe)
    
    assert isinstance(result, str)
    assert len(result) > 0


# ── Tests for Tool 3: create_fit_card ─────────────────────────────────────────

def test_create_fit_card_happy_path():
    """Happy path: generates caption from valid outfit string and item."""
    outfit = "Pair this jacket with dark jeans and boots for a 90s grunge look."
    new_item = {"title": "Leather Jacket", "price": 45, "platform": "depop"}
    result = create_fit_card(outfit, new_item)
    
    assert isinstance(result, str)
    assert len(result) > 0
    assert not result.startswith("Error:")

def test_create_fit_card_empty_outfit():
    """Failure mode: empty outfit string returns hardcoded error message."""
    result = create_fit_card("", {"title": "Test Item"})
    assert result == "Error: Missing outfit data to generate a fit card."

def test_create_fit_card_whitespace_outfit():
    """Edge case: whitespace-only outfit string is caught by the failure mode guard."""
    result = create_fit_card("   \n  ", {"title": "Test Item"})
    assert result == "Error: Missing outfit data to generate a fit card."