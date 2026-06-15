import gradio as gr
from agent import run_agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

def handle_query(user_query: str, wardrobe_choice: str, style_memory: str):
    if not user_query or not user_query.strip():
        return "Error: Please enter a description.", "", "", "", style_memory

    wardrobe = get_example_wardrobe() if wardrobe_choice == "Example wardrobe" else get_empty_wardrobe()
    session = run_agent(user_query, wardrobe, style_memory)

    if session.get("error"):
        return f"❌ {session['error']}", "", "", "", style_memory

    item = session["selected_item"]
    listing_text = f"🏷️ {item.get('title')}\n💵 Price: ${item.get('price')}\n📏 Size: {item.get('size')}\n🛒 Platform: {item.get('platform')}\n"
    
    if session.get("retry_message"):
        listing_text = f"{session['retry_message']}\n\n{listing_text}"
        
    price_trend_text = f"💰 {session.get('price_assessment')}\n\n📈 Trends: {session.get('trends')}"
    
    return listing_text, price_trend_text, session.get("outfit_suggestion"), session.get("fit_card"), session.get("style_memory")

def build_interface():
    with gr.Blocks(title="FitFindr") as demo:
        gr.Markdown("# FitFindr 🛍️\nFind secondhand pieces, check prices, spot trends, and get outfit ideas based on your wardrobe!")
        
        style_memory_state = gr.State("") # Stretch: Persists style memory

        with gr.Row():
            query_input = gr.Textbox(label="What are you looking for?", placeholder="e.g. vintage graphic tee under $30", scale=3)
            wardrobe_choice = gr.Radio(choices=["Example wardrobe", "Empty wardrobe (new user)"], value="Example wardrobe", label="Wardrobe", scale=1)
        submit_btn = gr.Button("Find it", variant="primary")

        with gr.Row():
            listing_output = gr.Textbox(label="🛍️ Top listing & Fallbacks", lines=6, interactive=False)
            price_trend_output = gr.Textbox(label="📊 Price & Trend Insights", lines=6, interactive=False)
        with gr.Row():
            outfit_output = gr.Textbox(label="👗 Outfit idea (Memory Aware)", lines=6, interactive=False)
            fitcard_output = gr.Textbox(label="✨ Your fit card", lines=6, interactive=False)

        submit_inputs = [query_input, wardrobe_choice, style_memory_state]
        submit_outputs = [listing_output, price_trend_output, outfit_output, fitcard_output, style_memory_state]
        
        submit_btn.click(fn=handle_query, inputs=submit_inputs, outputs=submit_outputs)
        query_input.submit(fn=handle_query, inputs=submit_inputs, outputs=submit_outputs)
    return demo

if __name__ == "__main__":
    demo = build_interface()
    demo.launch()