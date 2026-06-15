# FitFindr

FitFindr is a multi-tool AI agent that orchestrates a set of tools to help users find secondhand pieces, analyze pricing, track trends, and figure out how to style items with their existing wardrobe.

## Tool Inventory

1. **`search_listings`**:
   - **Inputs:** `description` (str), `size` (str | None), `max_price` (float | None)
   - **Outputs:** Returns a list of listing dictionaries, sorted by keyword relevance.
   - **Purpose:** Filters the mock dataset for clothing matches.

2. **`suggest_outfit`**:
   - **Inputs:** `new_item` (dict), `wardrobe` (dict), `trends` (str), `style_memory` (str)
   - **Outputs:** Returns a string with 1-2 paragraph outfit suggestions.
   - **Purpose:** Cross-references the new item with the user's closet and current trends.

3. **`create_fit_card`**:
   - **Inputs:** `outfit` (str), `new_item` (dict)
   - **Outputs:** Returns a short social media caption string.
   - **Purpose:** Generates a shareable "fit card".

## Stretch Features Documentation

1. **Price Comparison Tool:** - **How comparisons are made:** The tool loads the `listings.json` dataset, filters for all items that share the exact same `category` as the selected item, calculates the average price of those comparable listings, and compares the user's item price against that average to output a reasoned assessment.

2. **Style Profile Memory:** - **Storage approach:** The user's query history is appended to a string variable stored in Gradio's `gr.State()`. This allows the memory to persist across multiple interactions in the same browser session. The `gr.State()` object is fed back into the agent loop on every run without requiring the user to re-enter their preferences.

3. **Trend Awareness Tool:** - **Data source used:** The Groq LLM (`llama-3.3-70b-versatile`) acts as the dynamic data source. It is prompted to generate real-world streetwear and thrift fashion trends based on the requested size. This trend information visibly influences the output of `suggest_outfit`.

4. **Retry Logic with Fallback:** - **Handling zero-results:** When `search_listings` returns a zero-result search, the agent automatically retries with loosened constraints by removing the `size` and `max_price` parameters. It explicitly explains to the user what was adjusted via a warning message: *"⚠️ No exact matches found. We removed your size/price filters to find similar items!"*

## Planning Loop & Adaptive Logic

The agent uses an adaptive orchestration sequence with conditional branching. It extracts parameters via an LLM and queries `search_listings`.

If `search_listings` returns an empty list, the loop checks its state to see if filters were applied. If so, it branches to the Retry Logic (explained above). If `search_listings` still returns no results (a hard failure), the agent sets an error message and terminates the session immediately. **It does not call all tools unconditionally.** The agent behaves differently for the non-standard (empty) input compared to the happy path by halting execution before `suggest_outfit` or `create_fit_card` are ever reached.

## State Management Approach

State is managed via a single `session` dictionary initialized per interaction.

* **What is stored:** The original query, parsed JSON parameters, tool outputs (`search_results`, `selected_item`, `outfit_suggestion`, `fit_card`, `price_assessment`, `trends`), and any `error` or `retry_message`.

* **When it is stored:** Data is stored immediately after each tool executes.

* **How it passes between tools:** The planning loop acts as the orchestrator. Output from Tool 1 (stored in `session["selected_item"]`) is passed directly as an input argument to Tool 2 (`suggest_outfit(session["selected_item"], ...)`). Similarly, the output from Tool 2 passes to Tool 3 without any user re-entry.

## Error Handling

I have documented the specific failure modes for each required tool and successfully triggered them during testing:

* **`search_listings` (Triggered Failure):** If a query yields nothing (e.g., "designer ballgown size XXS under $5"), it returns `[]`. The agent loop catches this, skips outfit generation, and provides a specific, actionable response: *"No matching items found, even after expanding the search. Please try a different item."*

* **`suggest_outfit`:** If the user has an empty wardrobe (tested via `get_empty_wardrobe()`), the tool catches the empty list and alters its LLM prompt to offer *general styling advice* instead of crashing.

* **`create_fit_card`:** If passed an empty string, it bypasses the LLM entirely and returns a hardcoded error: *"Error: Missing outfit data to generate a fit card."*

## Demo Walkthrough

My demo showcases a complete multi-step workflow starting with a natural language query ("vintage graphic tee under \$30") and ending with a shareable fit card. To ensure all grading criteria are transparently documented, here is exactly what the agent does:

**1. End-to-End Workflow & State Management (Happy Path)**

* **Step 1:** The user submits a query. The agent calls `search_listings` to query the database and find matching inventory.

* **Step 2:** The exact item dictionary returned by `search_listings` is stored in the session state and passed directly into `suggest_outfit`—**without the user re-entering it**. The agent calls this tool to figure out how to match the item with the user's wardrobe.

* **Step 3:** The outfit suggestion text from `suggest_outfit` is then passed directly into `create_fit_card` **without re-entry**. The agent calls this tool to generate a shareable social media caption. All 3 tools are successfully called sequentially within a single interaction.

**2. Stretch Features Integration**

* **Price Comparison:** The demo shows the tool returning a price assessment with specific reasoning (comparing the item's price against the calculated average of comparable listings).

* **Trend Awareness:** The tool returns trend information (sourced from the Groq LLM) that visibly influences the text of the outfit suggestion.

* **Style Profile Memory:** The demo shows two separate interactions. The second interaction actively uses style preferences from the first (remembered via `gr.State()`) **without re-entry** by the user.

* **Retry Logic:** For a non-standard input with impossible filters ("levis jeans size XXS under \$5"), the demo shows the agent handling a zero-result search by automatically retrying with loosened constraints. It explicitly explains to the user what was adjusted ("We removed your size/price filters...").

**3. Deliberately Triggered Failure & Adaptive Logic**

* **Adaptive Behavior:** The agent behaves differently for a failing input compared to the happy path. When searching for a completely impossible item ("designer ballgown size XXS under \$5"), the agent **does not call all tools unconditionally** in the same sequence.

* **Actionable Error Handling:** This deliberately triggered actual failure results in an empty list from the initial search and the retry. The loop safely halts, and the agent's response is specific and actionable. It tells the user exactly what failed and what to try next: *"No matching items found, even after expanding the search. Please try a different item."*


## Spec Reflection

Writing `planning.md` helped drastically by forcing me to define the exact parameter names and types before writing the LLM prompts. Without it, `suggest_outfit` would have hallucinated the wardrobe keys. One divergence from my original spec was the implementation of "Style Profile Memory"; originally I planned to save it to a JSON file, but utilizing Gradio's `gr.State` proved much cleaner for the lifecycle of the agent loop.

## AI Usage Transparency

I plugged the specifications into Gemini and copied the generated code directly to build my project. Specifically:

1. **Tool Generation:** I provided the `planning.md` Tool 1 and Tool 2 sections and directed Gemini to write the Python functions. I reviewed and revised the generated code to ensure it didn't throw exceptions on empty inputs (specifically overriding the LLM when it tried to raise a `ValueError` for an empty wardrobe).

2. **Loop Orchestration:** I provided my Architecture ASCII diagram and directed Gemini to build the `run_agent` orchestration loop. I manually revised the code it generated to insert the Stretch "Retry logic", ensuring it properly cleared the size/price filters before attempting the fallback search.