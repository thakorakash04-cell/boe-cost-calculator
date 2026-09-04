import os
import streamlit as st
import pandas as pd
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from boe_extractor import extract_boe_data
from calculation_engine import compute_boe_costing
from excel_generator import populate_boe_excel

st.set_page_config(page_title="BOE Cost Calculator", layout="wide", page_icon="📄")

# ── Custom Styling ──
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a5276 0%, #2e86c1 100%);
        padding: 15px 20px;
        border-radius: 10px;
        color: white !important;
    }
    div[data-testid="stMetric"] label { color: #d4e6f1 !important; font-size: 13px !important; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: white !important; font-size: 22px !important; }
    .yellow-badge {
        display: inline-block;
        background: #FFFF00;
        color: #333;
        padding: 2px 10px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
        margin-left: 5px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📄 BOE Cost Calculation & Automation Tool")
st.markdown("Upload a **Bill of Entry PDF** → AI extracts data automatically → Compute landed costs → Download filled Excel.")

# ── Sidebar ──
st.sidebar.header("⚙️ Settings")
api_key = st.sidebar.text_input(
    "Google AI Studio API Key (FREE)",
    type="password",
    value=os.environ.get("GOOGLE_API_KEY", ""),
    help="Free from https://aistudio.google.com/apikey"
)
st.sidebar.markdown("---")
st.sidebar.markdown("**Get your FREE API Key:**")
st.sidebar.markdown("1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)")
st.sidebar.markdown("2. Sign in with your Google account")
st.sidebar.markdown('3. Click **"Create API Key"**')
st.sidebar.markdown("4. Copy & paste it above")
st.sidebar.markdown("---")
st.sidebar.info("Free tier: **15 requests/minute, 1M tokens/day** — enough for hundreds of BOEs daily!")

# ── Session State ──
if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = None
if "computed_results" not in st.session_state:
    st.session_state.computed_results = None
if "excel_bytes" not in st.session_state:
    st.session_state.excel_bytes = None
if "mode" not in st.session_state:
    st.session_state.mode = None

# ══════════════════════════════════════════════════════════════
# MODE SELECTION
# ══════════════════════════════════════════════════════════════
if st.session_state.mode is None and st.session_state.extracted_data is None:
    st.markdown("---")
    st.subheader("How would you like to enter BOE data?")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🤖 AI Extraction (Recommended)")
        st.markdown("Upload BOE PDF → AI reads it automatically")
        st.caption("Works with scanned, printed & digital BOEs. Uses FREE Gemini AI.")
        if st.button("Upload BOE PDF", use_container_width=True, type="primary"):
            st.session_state.mode = "ai"
            st.rerun()

    with c2:
        st.markdown("### ✍️ Manual Entry")
        st.markdown("Type in the BOE details yourself")
        st.caption("No API key needed — works completely offline!")
        if st.button("Enter Data Manually", use_container_width=True):
            st.session_state.mode = "manual"
            st.session_state.extracted_data = {
                "header": {
                    "total_weight_kg": 0.0,
                    "exchange_rate": 0.0,
                    "invoice_value_fc": 0.0,
                    "freight_inr": 0.0,
                    "insurance_percent": 0.0,
                    "misc_charges": 0.0,
                },
                "items": [
                    {"sr_no": 1, "material_name": "", "unit_price_fc": 0.0, "quantity": 0.0, "bcd_rate_percent": 0.0, "sws_rate_percent": 10.0, "igst_rate_percent": 18.0, "hsn_code": ""}
                ]
            }
            st.rerun()

# ══════════════════════════════════════════════════════════════
# AI MODE: Upload & Extract
# ══════════════════════════════════════════════════════════════
if st.session_state.mode == "ai" and st.session_state.extracted_data is None:
    st.markdown("---")
    if st.button("← Back to Mode Selection"):
        st.session_state.mode = None
        st.rerun()

    uploaded_file = st.file_uploader(
        "Upload Bill of Entry (PDF)",
        type=["pdf"],
        help="Upload scanned, printed, or digital BOE PDFs from ICEGATE / Customs"
    )

    if uploaded_file:
        st.info(f"📄 Uploaded: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")

        if st.button("🚀 Extract BOE Data with FREE AI", type="primary", use_container_width=True):
            if not api_key:
                st.error(
                    "⚠️ Please paste your Google AI API Key in the sidebar first.\n\n"
                    "**It's FREE:** Get it from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)"
                )
            else:
                with st.spinner("🔍 AI is reading your BOE document... This may take 15-30 seconds."):
                    temp_pdf = f"temp_{uploaded_file.name}"
                    with open(temp_pdf, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    try:
                        data = extract_boe_data(temp_pdf, api_key=api_key)
                        st.session_state.extracted_data = data
                        st.success("✅ Extraction Successful! Review the extracted data below.")
                        if os.path.exists(temp_pdf):
                            os.remove(temp_pdf)
                        st.rerun()
                    except Exception as e:
                        error_msg = str(e)
                        if "API key" in error_msg.lower() or "invalid" in error_msg.lower():
                            st.error(
                                "🔑 **Invalid API Key.** Please check your Google AI Studio key.\n\n"
                                "Get a new one free: [aistudio.google.com/apikey](https://aistudio.google.com/apikey)"
                            )
                        else:
                            st.error(f"❌ Extraction failed: {e}")
                        if os.path.exists(temp_pdf):
                            os.remove(temp_pdf)

# ══════════════════════════════════════════════════════════════
# STEP 1 & 2: Edit Header + Items (Both modes land here)
# ══════════════════════════════════════════════════════════════
if st.session_state.extracted_data:
    st.markdown("---")

    if st.button("🔄 Start Over (New BOE)"):
        st.session_state.extracted_data = None
        st.session_state.computed_results = None
        st.session_state.excel_bytes = None
        st.session_state.mode = None
        st.rerun()

    # ── STEP 1: Header Inputs ──
    st.markdown("#### 1️⃣ Header Inputs <span class='yellow-badge'>INPUT CELLS</span>", unsafe_allow_html=True)
    st.caption("These values fill cells C5 to C10 on the **Input Form** sheet.")

    header_data = st.session_state.extracted_data.get("header", {})

    col1, col2, col3 = st.columns(3)
    with col1:
        total_weight_kg = st.number_input("📦 Total Weight (Kg)", value=float(header_data.get("total_weight_kg") or 0.0), format="%.2f", min_value=0.0)
        exchange_rate = st.number_input("💱 Exchange Rate (e.g. 83.50 for USD)", value=float(header_data.get("exchange_rate") or 0.0), format="%.2f", min_value=0.0)
    with col2:
        invoice_value_fc = st.number_input("💰 Invoice Value ($)", value=float(header_data.get("invoice_value_fc") or 0.0), format="%.2f", min_value=0.0)
        freight_inr = st.number_input("🚚 Freight (₹)", value=float(header_data.get("freight_inr") or 0.0), format="%.2f", min_value=0.0)
    with col3:
        insurance_percent = st.number_input("🛡️ Insurance (%)", value=float(header_data.get("insurance_percent") or 0.0), format="%.4f", min_value=0.0)
        misc_charges = st.number_input("📋 Miscellaneous Charges", value=float(header_data.get("misc_charges") or 0.0), format="%.2f", min_value=0.0)

    # ── STEP 2: Line Items ──
    st.markdown("---")
    st.markdown("#### 2️⃣ Material / Line Items <span class='yellow-badge'>INPUT CELLS</span>", unsafe_allow_html=True)
    st.caption("These fill rows B15:E34 on the **Input Form** sheet. Add/remove rows as needed.")

    items = st.session_state.extracted_data.get("items", [])
    df_items = pd.DataFrame(items)

    if "sr_no" not in df_items.columns:
        df_items.insert(0, "sr_no", range(1, len(df_items) + 1))

    expected_cols = ["sr_no", "material_name", "unit_price_fc", "quantity", "bcd_rate_percent", "sws_rate_percent", "igst_rate_percent", "hsn_code"]
    for c in expected_cols:
        if c not in df_items.columns:
            if c.endswith("_percent"):
                df_items[c] = 10.0 if "sws" in c else (18.0 if "igst" in c else 0.0)
            else:
                df_items[c] = ""

    display_cols = ["sr_no", "material_name", "hsn_code", "quantity", "unit_price_fc", "bcd_rate_percent", "sws_rate_percent", "igst_rate_percent"]
    grid_data = df_items[display_cols].copy()

    column_config = {
        "sr_no": st.column_config.NumberColumn("Sr. No", width="small"),
        "material_name": st.column_config.TextColumn("Material Name / Description", width="large"),
        "hsn_code": st.column_config.TextColumn("HSN Code", width="medium"),
        "quantity": st.column_config.NumberColumn("Quantity", format="%.2f"),
        "unit_price_fc": st.column_config.NumberColumn("Unit Price ($)", format="%.2f"),
        "bcd_rate_percent": st.column_config.NumberColumn("BCD Rate (%)", format="%.2f"),
        "sws_rate_percent": st.column_config.NumberColumn("SWS Rate (%)", format="%.2f"),
        "igst_rate_percent": st.column_config.NumberColumn("IGST Rate (%)", format="%.2f"),
    }

    edited_df = st.data_editor(grid_data, num_rows="dynamic", use_container_width=True, column_config=column_config)

    header_payload = {
        "total_weight_kg": total_weight_kg,
        "exchange_rate": exchange_rate,
        "invoice_value_fc": invoice_value_fc,
        "freight_inr": freight_inr,
        "insurance_percent": insurance_percent,
        "misc_charges": misc_charges
    }
    items_payload = edited_df.to_dict(orient="records")

    st.markdown("---")
    if st.button("🧮 Compute Landed Costs & Generate Excel", type="primary", use_container_width=True):
        if exchange_rate <= 0:
            st.error("⚠️ Exchange Rate must be greater than 0")
        elif invoice_value_fc <= 0:
            st.error("⚠️ Invoice Value must be greater than 0")
        elif len(items_payload) == 0:
            st.error("⚠️ Please add at least one material item")
        else:
            try:
                results = compute_boe_costing(header_payload, items_payload)
                st.session_state.computed_results = results
                excel_bytes = populate_boe_excel(header_payload, items_payload)
                st.session_state.excel_bytes = excel_bytes
                st.success("✅ Calculations complete! Scroll down for results & download.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Calculation Error: {e}")

# ══════════════════════════════════════════════════════════════
# STEP 3 & 4: Results + Download
# ══════════════════════════════════════════════════════════════
if st.session_state.computed_results:
    st.markdown("---")
    res = st.session_state.computed_results
    head_res = res["header"]
    item_res = res["items"]

    st.subheader("3️⃣ Customs Valuation & Landed Cost Summary")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Assessable Value (INR)", f"₹ {head_res['total_assessable_value']:,.2f}")
    k2.metric("Total BCD", f"₹ {head_res['total_bcd']:,.2f}")
    k3.metric("Total IGST", f"₹ {head_res['total_igst']:,.2f}")
    k4.metric("Total Duty (BCD+SWS+IGST)", f"₹ {head_res['total_duty']:,.2f}")

    st.subheader("Calculated Line Items")
    df_res = pd.DataFrame(item_res)
    display_result_cols = {
        "sr_no": st.column_config.NumberColumn("Sr.No"),
        "material_name": st.column_config.TextColumn("Material"),
        "item_assess_value": st.column_config.NumberColumn("Assess Value (₹)", format="₹ %.2f"),
        "item_bcd": st.column_config.NumberColumn("BCD (₹)", format="₹ %.2f"),
        "item_sws": st.column_config.NumberColumn("SWS (₹)", format="₹ %.2f"),
        "item_igst": st.column_config.NumberColumn("IGST (₹)", format="₹ %.2f"),
        "item_total_duty": st.column_config.NumberColumn("Total Duty (₹)", format="₹ %.2f"),
        "unit_cost_quoted_inr": st.column_config.NumberColumn("Unit Cost Quoted (₹)", format="₹ %.2f"),
        "unit_cost_actual_with_duty_gst": st.column_config.NumberColumn("Unit Cost + Duty + GST (₹)", format="₹ %.2f"),
        "actual_cost_excl_gst": st.column_config.NumberColumn("Actual Cost Excl GST (₹)", format="₹ %.2f"),
    }
    st.dataframe(
        df_res[list(display_result_cols.keys())],
        column_config=display_result_cols,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")
    st.subheader("4️⃣ Download Completed Excel")
    st.caption("This is your original `BOE Cost Calculation Form.xlsx` with all input cells filled and all formulas active in Excel.")

    if st.session_state.excel_bytes:
        st.download_button(
            label="⬇️ Download BOE_Cost_Calculation_Form_Filled.xlsx",
            data=st.session_state.excel_bytes,
            file_name="BOE_Cost_Calculation_Form_Filled.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
