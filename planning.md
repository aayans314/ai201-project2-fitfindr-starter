# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

## Tools

### Tool 1: search_listings

**What it does:**
Searches the mock listings dataset for items matching the user's description, with optional filters for size and maximum price.

**Input parameters:**

* `description` (str): Keywords describing the item the user is looking for (e.g., "vintage graphic tee").

* `size` (str | None): Size string to filter by. Matching is case-insensitive. None to skip.

* `max_price` (float | None): Maximum price ceiling (inclusive). None to skip.

**What it returns:**
A list of matching listing dictionaries, sorted by relevance score (highest keyword overlap first).

**What happens if it fails or returns nothing:**
Returns an empty list `[]` if no listings match. It does NOT raise an exception. The planning loop will handle the empty list.

### Tool 2: suggest_outfit

**What it does:**
Generates 1–2 complete outfit combinations using a newly thrifted item, the user's existing wardrobe, current trends, and their past style memory.

**Input parameters:**

* `new_item` (dict): The listing dictionary of the item selected from the search results.

* `wardrobe` (dict): A dictionary containing an `items` list of wardrobe item dicts.

* `trends` (str): Context string containing current fashion trends.

* `style_memory` (str): Context string containing the user's past queries for personalization.

**What it returns:**
A non-empty string containing LLM-generated style suggestions incorporating the `new_item` with specific pieces from the `wardrobe`.

**What happens if it fails or returns nothing:**
If `wardrobe['items']` is empty, the tool modifies its prompt to request **general styling advice** for the `new_item` instead of attempting to match it with specific wardrobe pieces. It does NOT crash.

### Tool 3: create_fit_card

**What it does:**
Generates a short, shareable outfit caption (2-4 sentences) for social media, incorporating the item's details and the suggested outfit vibe.

**Input parameters:**

* `outfit` (str): The outfit suggestion string returned by `suggest_outfit()`.

* `new_item` (dict): The listing dictionary for the thrifted item.

**What it returns:**
A 2–4 sentence string formatted as a casual Instagram/TikTok caption, mentioning the item name, price, and platform.

**What happens if it fails or returns nothing:**
If the `outfit` string is empty, missing, or whitespace-only, the tool bypasses the LLM and directly returns a descriptive error message string. It does NOT raise an exception.

### Additional Tools (Stretch Features)

**Tool 4: compare_price (Price Comparison Tool)**

* **Inputs:** `new_item` (dict)

* **Outputs:** String assessing if the price is a good deal compared to the category average.

* **Failure Mode:** Returns a safe fallback string if no comparable items exist in the dataset.

**Tool 5: get_trending_styles (Trend Awareness Tool)**

* **Inputs:** `size` (str | None)

* **Outputs:** String summarizing 2 current streetwear/thrift trends.

* **Failure Mode:** Returns a safe fallback string if the LLM generation fails.

## Planning Loop

**How does your agent decide which tool to call next?**
The planning loop executes a strict sequence of conditional logic:

 1. Initialize a new session using `_new_session(query, wardrobe, style_memory)`.

 2. Parse the natural language `query` (using an LLM call) to extract `description`, `size`, and `max_price`.

 3. Call `search_listings` using the parsed parameters.

 4. **Condition A (Retry Logic Fallback):** If `search_results` is empty `[]` BUT the user provided a `size` or `max_price` filter, the agent automatically retries with loosened constraints (removes the filters). It sets a `retry_message` in the session explaining to the user what was adjusted.

 5. **Condition B (Hard Failure):** If `search_results` is still empty after the retry, set `session["error"] = "No matching items found."` and return the `session` immediately. Halt execution. It does NOT call suggest_outfit unconditionally.

 6. **Condition C (Success):** Set `session["selected_item"] = session["search_results"][0]`.

 7. Call `compare_price` and `get_trending_styles` to populate stretch feature states.

 8. Call `suggest_outfit` passing the item, wardrobe, trends, and memory. Store in `session["outfit_suggestion"]`.

 9. Call `create_fit_card` passing the outfit and item. Store in `session["fit_card"]`.

10. Return the complete `session` object.

## State Management

**How does information from one tool get passed to the next?**
State is managed entirely within the `session` dictionary initialized at the start of the interaction. Tools do not communicate with each other directly. The planning loop orchestrates the data flow by taking the returned output of one tool, saving it into the `session` dictionary (e.g., `session["selected_item"]`), and passing that exact value to the next tool (`suggest_outfit(session["selected_item"], ...)`). This ensures data flows without the user re-entering it.

**Style Profile Memory (Stretch):** User query history is appended to a `style_memory` string. Gradio's `gr.State()` persists this string across multiple front-end interactions and feeds it back into the agent loop on every run.

## Error Handling

| Tool | Failure mode | Agent response | 
| ----- | ----- | ----- | 
| `search_listings` | No results match the query. | Agent catches the empty list, attempts to retry without filters, and if it still fails, sets `session["error"]` explaining what failed and halts the loop. | 
| `suggest_outfit` | `wardrobe['items']` is empty. | Tool detects the empty list and prompts the LLM for general styling advice instead of specific matching. | 
| `create_fit_card` | `outfit` input is empty/missing. | Tool returns a hardcoded error string instead of hitting the LLM. | 

## Architecture

    User Query & Wardrobe Dict
        │
        ▼
    [ Parse Query (LLM or Regex) ] 
        │
        ▼
    Session: session["parsed"]
        │
        ▼
    [ search_listings(description, size, max_price) ]
        │
        ├─► (results == [] & filters used) ──► Retry without filters
        │
        ├─► (results == []) ───► Session: session["error"] = "No matches" ──► RETURN EARLY
        │
        ▼ (results != [])
    Session: session["selected_item"] = results[0]
        │
        ├─► [ compare_price() ] ──► Session: session["price_assessment"]
        │
        ├─► [ get_trending_styles() ] ──► Session: session["trends"]
        │
        ▼
    [ suggest_outfit(selected_item, wardrobe, trends, memory) ]
        │
        ├─► (wardrobe empty) ──► Prompt LLM for general style advice ────┐
        │                                                                │
        ├─► (wardrobe full) ───► Prompt LLM to match with specific items ┤
        │                                                                │
        ▼                                                                │
    Session: session["outfit_suggestion"] <──────────────────────────────┘
        │
        ▼
    [ create_fit_card(outfit_suggestion, selected_item) ]
        │
        ├─► (outfit missing) ──► Session: session["error"] = "Missing outfit data" ──► RETURN EARLY
        │
        ▼ (success)
    Session: session["fit_card"] = "..."
        │
        ▼
    RETURN SESSION

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**
I will use Gemini to implement the tools.

* For `search_listings`: I will provide the Tool 1 spec and ask it to use `load_listings()`. **Verification:** I will test it with a query guaranteed to fail (e.g., "designer ballgown") and assert it returns `[]` without throwing a Python error.

* For `suggest_outfit`: I will provide the Tool 2 spec. **Verification:** I will run it once passing `get_example_wardrobe()` and once passing `get_empty_wardrobe()`. I will verify the LLM output shifts to general styling advice.

* For `create_fit_card`: I will provide the Tool 3 spec. **Verification:** I will pass an empty string `""` for the outfit argument to guarantee the hardcoded error string is triggered.

**Milestone 4 — Planning loop and state management:**
I will use Gemini to implement `agent.py`.

* I will provide the "Planning Loop", "State Management", and "Architecture" sections of this document.

* **Verification:** I will run the CLI test block provided in `agent.py`. I will verify the "Happy path" reaches the end and the "No-results path" triggers early termination.

## A Complete Interaction (Step by Step Walkthrough for Demo)

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers."

**Step 1 (Happy Path & State Flow):**
The agent extracts `description="vintage graphic tee"`, `size=None`, and `max_price=30.0`. It calls `search_listings()`. It returns a list of matching items, and the agent selects the highest-scoring match. The demo shows this exact item passing into `suggest_outfit` without user re-entry.

**Step 2 (Stretch - Price & Trends):**
The agent calls `compare_price()` and `get_trending_styles()` to populate context for the outfit generation. The demo shows these insights returning in the UI.

**Step 3 (Stretch - Style Profile Memory):**
The agent calls `suggest_outfit()` passing the selected tee, the user's `wardrobe`, recent trends, and the `style_memory`. The demo shows a second interaction where the user's past query influences the outfit suggestion without them re-entering their preferences.

**Step 4 (Stretch - Retry Logic):**
If the user searches for an impossible constraint ("levis jeans size XXS under $5"), the demo shows `search_listings` returning zero results, triggering the fallback. The agent loosens constraints, retries, and shows a message explaining what was adjusted.

**Step 5 (Deliberately Triggered Failure):**
If the user searches for "designer ballgown size XXS under $5", the demo shows a hard failure. The agent response is specific and actionable: *"No matching items found, even after expanding the search. Please try a different item."* The loop halts cleanly.