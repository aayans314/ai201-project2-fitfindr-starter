# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

### Tool 1: search_listings

**What it does:**
Searches the mock listings dataset for items matching the user's description, with optional filters for size and maximum price. 

**Input parameters:**
- `description` (str): Keywords describing the item the user is looking for (e.g., "vintage graphic tee").
- `size` (str | None): Size string to filter by. Matching is case-insensitive. None to skip.
- `max_price` (float | None): Maximum price ceiling (inclusive). None to skip.

**What it returns:**
A list of matching listing dictionaries, sorted by relevance score (highest keyword overlap first). Drop any listings with a score of 0.

**What happens if it fails or returns nothing:**
Returns an empty list `[]` if no listings match. It does NOT raise an exception. The planning loop will handle the empty list.

---

### Tool 2: suggest_outfit

**What it does:**
Generates 1–2 complete outfit combinations using a newly thrifted item and the user's existing wardrobe.

**Input parameters:**
- `new_item` (dict): The listing dictionary of the item selected from the search results.
- `wardrobe` (dict): A dictionary containing an `items` list of wardrobe item dicts.

**What it returns:**
A non-empty string containing LLM-generated style suggestions incorporating the `new_item` with specific pieces from the `wardrobe`.

**What happens if it fails or returns nothing:**
If `wardrobe['items']` is empty, the tool modifies its prompt to the LLM to request **general styling advice** for the `new_item` (e.g., "pair this with wide-leg jeans") instead of attempting to match it with specific wardrobe pieces. It does NOT crash or raise an exception.

---

### Tool 3: create_fit_card

**What it does:**
Generates a short, shareable outfit caption (2-4 sentences) for social media, incorporating the item's details and the suggested outfit vibe.

**Input parameters:**
- `outfit` (str): The outfit suggestion string returned by `suggest_outfit()`.
- `new_item` (dict): The listing dictionary for the thrifted item.

**What it returns:**
A 2–4 sentence string formatted as a casual Instagram/TikTok caption, mentioning the item name, price, and platform naturally.

**What happens if it fails or returns nothing:**
If the `outfit` string is empty, missing, or whitespace-only, the tool bypasses the LLM and directly returns a descriptive error message string (e.g., "Error: Missing outfit data to generate a fit card."). It does NOT raise an exception.

---

## Planning Loop

**How does your agent decide which tool to call next?**
The planning loop executes a strict sequence of conditional logic:

1. Initialize a new session using `_new_session(query, wardrobe)`.
2. Parse the natural language `query` (using an LLM call) to extract `description`, `size`, and `max_price`. Store these in `session["parsed"]`.
3. Call `search_listings` using the parsed parameters. Store the return value in `session["search_results"]`.
4. **Condition A (Failure):** If `session["search_results"]` is empty, set `session["error"] = "No matching items found."` and return the `session` immediately. Halt execution.
5. **Condition B (Success):** If `session["search_results"]` is not empty, set `session["selected_item"] = session["search_results"][0]`.
6. Call `suggest_outfit` passing `session["selected_item"]` and `session["wardrobe"]`. Store the return value in `session["outfit_suggestion"]`.
7. Call `create_fit_card` passing `session["outfit_suggestion"]` and `session["selected_item"]`. Store the return value in `session["fit_card"]`.
8. Return the complete `session` object.

---

## State Management

**How does information from one tool get passed to the next?**
State is managed entirely within the `session` dictionary initialized at the start of the interaction. Tools do not communicate with each other directly. The planning loop orchestrates the data flow by taking the returned output of one tool, saving it into a specific key in the `session` dictionary (e.g., `session["selected_item"]`), and passing that exact value as the input argument to the next tool.

---

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No results match the query. | Tool returns `[]`. Agent catches the empty list, sets `session["error"]` to inform the user, and halts the loop. |
| `suggest_outfit` | `wardrobe['items']` is empty. | Tool detects the empty list and prompts the LLM for general styling advice instead of specific matching. The loop continues normally. |
| `create_fit_card` | `outfit` input is empty/missing. | Tool returns a hardcoded error string. The loop finishes, but the user sees the error message instead of a valid fit card. |

---

## Architecture

```text
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
    ├─► (results == []) ───► Session: session["error"] = "No matches" ──► RETURN EARLY
    │
    ▼ (results != [])
Session: session["selected_item"] = results[0]
    │
    ▼
[ suggest_outfit(selected_item, wardrobe) ]
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
```

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**
I will use Gemini to implement the tools. 
- For `search_listings`: I will provide the Tool 1 spec and ask it to use `load_listings()`. **Verification:** I will test it with a query guaranteed to fail (e.g., "designer ballgown under $5") and assert it returns `[]` without throwing a Python error.
- For `suggest_outfit`: I will provide the Tool 2 spec. **Verification:** I will run it once passing `get_example_wardrobe()` and once passing `get_empty_wardrobe()`. I will verify the LLM output shifts from specific item matching to general styling advice.
- For `create_fit_card`: I will provide the Tool 3 spec. **Verification:** I will pass an empty string `""` for the outfit argument to guarantee the hardcoded error string is triggered.

**Milestone 4 — Planning loop and state management:**
I will use Gemini to implement `agent.py`.
- I will provide the "Planning Loop", "State Management", and "Architecture" sections of this document.
- **Verification:** I will run the CLI test block provided in `agent.py`. I will verify the "Happy path" reaches the end and prints the fit card, and the "No-results path" triggers the early termination and prints the specific error message defined in Step 4 of the loop.

---

## A Complete Interaction (Step by Step)

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent calls an LLM to parse the query and extracts `description="vintage graphic tee"`, `size=None`, and `max_price=30.0`. It calls `search_listings()` with these parameters. It returns a list of matching items, and the agent selects the highest-scoring match (e.g., "Y2K Baby Tee — Butterfly Print").

**Step 2:**
The agent calls `suggest_outfit()` passing the selected baby tee dictionary and the user's `wardrobe` dictionary. Because the user is new, the wardrobe dictionary is currently empty. The tool handles this by prompting the LLM for general styling advice (e.g., "Pair this baby tee with some low-rise baggy jeans and your favorite chunky sneakers"). 

**Step 3:**
The agent calls `create_fit_card()` passing the general styling advice and the baby tee dictionary. The LLM generates a shareable caption: "just scored this y2k butterfly tee for $18 on depop 🦋 can't wait to throw this on with baggy denim and chunky kicks. #thrifted".

**Final output to user:**
The interaction concludes successfully. The user sees the title of the item found (`session["selected_item"]["title"]`), the styling advice (`session["outfit_suggestion"]`), and the final social media caption (`session["fit_card"]`).