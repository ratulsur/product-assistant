# app.py
from pathlib import Path
import sys
import os
import io
import csv
import streamlit as st

# --- project root on sys.path so absolute imports work if backend exists ---
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# --- Try real backend; if missing, fall back to mocks ---
BACKEND_OK = True
try:
    from prod_assistant.etl.data_scraper import FlipkartScraper  # change to data_scrapper if that's your filename
    from prod_assistant.etl.data_ingestion import DataIngestion
except Exception as _e:
    BACKEND_OK = False

    class FlipkartScraper:  # Mock
        def scrape_flipkart_products(self, query, max_products=1, review_count=2):
            # Minimal demo rows: [rank, product_name, price, rating, review_text]
            return [
                [1, f"{query} — Demo Variant A", "₹1,999", 4.2, "Solid budget pick."],
                [2, f"{query} — Demo Variant B", "₹2,499", 4.0, "Decent for the price."],
            ][:max_products]

        def save_to_csv(self, rows, out_path):
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["rank", "product_name", "price", "rating", "review"])
                writer.writerows(rows)

    class DataIngestion:  # Mock that raises to block ingestion
        def run_pipeline(self):
            raise RuntimeError("Backend ingestion not implemented yet (mock mode).")


# --- UI ---
st.title("📦 Product Review Scraper")

if not BACKEND_OK:
    st.sidebar.warning("⚠️ MOCK MODE: Backend imports missing. Using demo data.")
    st.caption("Running in mock mode until backend is ready (imports failed).")

OUTPUT = ROOT / "data" / "product_reviews.csv"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

# session init
if "product_inputs" not in st.session_state:
    st.session_state.product_inputs = [""]

def add_product_input():
    st.session_state.product_inputs.append("")

st.subheader("📝 Optional Product Description")
product_description = st.text_area(
    "Enter product description (used as an extra search keyword):",
    placeholder="e.g., 'wireless headphones, ANC'"
)

st.subheader("🛒 Product Names")
updated_inputs = []
for i, val in enumerate(st.session_state.product_inputs):
    input_val = st.text_input(f"Product {i+1}", value=val, key=f"product_{i}")
    updated_inputs.append(input_val)
st.session_state.product_inputs = updated_inputs

st.button("➕ Add Another Product", on_click=add_product_input, key="add_btn")

max_products = st.number_input("How many products per search?", min_value=1, max_value=10, value=1)
review_count = st.number_input("How many reviews per product?", min_value=1, max_value=10, value=2)

scraper = FlipkartScraper()

if st.button("🚀 Start Scraping", key="scrape_btn"):
    product_inputs = [p.strip() for p in st.session_state.product_inputs if p.strip()]
    if product_description.strip():
        product_inputs.append(product_description.strip())

    if not product_inputs:
        st.warning("⚠️ Please enter at least one product name or a product description.")
    else:
        final_data = []
        for query in product_inputs:
            st.write(f"🔍 Searching for: {query}")
            results = scraper.scrape_flipkart_products(
                query, max_products=max_products, review_count=review_count
            )
            final_data.extend(results or [])

        # de-dup on product_name at index 1
        unique = {}
        for row in final_data:
            if isinstance(row, (list, tuple)) and len(row) > 1:
                key = row[1]
                if key not in unique:
                    unique[key] = row
        final_data = list(unique.values())

        st.session_state["scraped_data"] = final_data
        scraper.save_to_csv(final_data, str(OUTPUT))
        st.success(f"✅ Data saved to `{OUTPUT.as_posix()}`")

        # Safer download: open and read bytes
        with open(OUTPUT, "rb") as f:
            st.download_button(
                "📥 Download CSV",
                data=f,
                file_name="product_reviews.csv",
                mime="text/csv"
            )

# Ingestion: enabled only if real backend present
ingest_disabled = not BACKEND_OK
if "scraped_data" in st.session_state:
    if ingest_disabled:
        st.button("🧠 Store in Vector DB (AstraDB)", disabled=True, help="Enable after backend is ready.")
        st.info("Backend not wired yet. Once `prod_assistant.etl.data_ingestion.DataIngestion` is implemented, this will activate.")
    else:
        if st.button("🧠 Store in Vector DB (AstraDB)", key="ingest_btn"):
            with st.spinner("📡 Initializing ingestion pipeline..."):
                try:
                    ingestion = DataIngestion()
                    st.info("🚀 Running ingestion pipeline...")
                    ingestion.run_pipeline()
                    st.success("✅ Data successfully ingested to AstraDB!")
                except Exception as e:
                    st.error("❌ Ingestion failed!")
                    st.exception(e)
