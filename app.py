# app.py

import os
import logging
from dotenv import load_dotenv
load_dotenv(override=True)

logger = logging.getLogger(__name__)

import streamlit as st
import pandas as pd
from datetime import datetime

# Import skills and utilities
from utils.categories import (
    CATEGORIES, BUDGET_LIMITS, load_categories_from_sheets, 
    add_category, delete_category, update_category_keywords, 
    count_transactions_with_category
)
from utils.sheets_handler import sheets_handler, get_friendly_error_message
from skills.text_parser import parse_text, clarify_pending_transaction, generate_general_response
from skills.classifier import classify_transaction
from skills.sheets_writer import write_to_sheets
from skills.analytics import generate_analytics
from skills.correction import correct_transaction
from skills.pdf_parsing_skill import parse_pdf, parse_image

# Page configuration
st.set_page_config(
    page_title="FamilyBudget AI Assistant",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom styling for premium wowed aesthetics matching the design banner
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=Inter:wght@300;400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Container padding and max-width */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1.5rem !important;
        padding-left: 4rem !important;
        padding-right: 4rem !important;
        max-width: 1400px !important;
    }
    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 0.5rem !important;
    }
    
    /* Default image rendering inside containers */
    div[data-testid="stImage"] img {
        width: 100% !important;
        display: block !important;
    }
    
    /* Premium background gradient for the main content area */
    .stApp {
        background: radial-gradient(circle at 80% 20%, #f3faf6 0%, #e5ede7 100%) !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        color: #0b1a11 !important;
        letter-spacing: -0.5px !important;
        margin-top: 0.2rem !important;
        margin-bottom: 0.4rem !important;
    }
    
    /* Custom Sidebar styling matching rich dark forest green */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0B291A 0%, #071E13 100%) !important;
        border-right: 1px solid rgba(0, 230, 118, 0.12) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #d0e5d5;
    }
    .sidebar-logo-title {
        color: #00E676 !important;
        font-size: 1.6rem !important;
        font-weight: 800 !important;
        font-family: 'Outfit', sans-serif !important;
        margin: 0 !important;
        line-height: 1.1 !important;
        letter-spacing: -0.5px !important;
    }
    
    /* Hide the radio button label & circles & style option items */
    div[data-testid="stRadio"] label[data-testid="stWidgetLabel"] {
        display: none !important;
    }
    div[data-testid="stRadio"] > div {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
    }
    div[data-testid="stRadio"] label {
        background: transparent !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 10px 14px !important;
        margin-bottom: 6px !important;
        color: #d0e5d5 !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        width: 100% !important;
    }
    div[data-testid="stRadio"] label:hover {
        background: rgba(255, 255, 255, 0.05) !important;
        color: #ffffff !important;
    }
    div[data-testid="stRadio"] label:has(input:checked) {
        background: #00E676 !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(0, 230, 118, 0.25) !important;
    }
    div[data-testid="stRadio"] label:has(input:checked) * {
        color: #041F10 !important;
        font-weight: 700 !important;
    }
    div[data-testid="stRadio"] label > div:first-of-type {
        display: none !important;
    }
    div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] {
        padding-left: 0 !important;
    }
    
    /* Dark-themed selectbox */
    div[data-testid="stSelectbox"] > div {
        background-color: #1A1A1A !important;
        border: 1px solid #2E7D32 !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stSelectbox"] div[role="button"], 
    div[data-testid="stSelectbox"] [data-baseweb="select"] * {
        color: #FFFFFF !important;
    }
    div[data-testid="stSelectbox"] svg {
        fill: #4CAF50 !important;
    }
    div[data-testid="stSelectbox"] > div:hover {
        border-color: #4CAF50 !important;
    }
    div[data-testid="stSelectbox"] label {
        color: #8da382 !important;
        font-size: 0.8rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }
    
    /* Premium Glassmorphism Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        border: 1px solid rgba(0, 135, 90, 0.08) !important;
        box-shadow: 0 8px 32px 0 rgba(0, 87, 58, 0.03) !important;
        margin-bottom: 20px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    .glass-card:hover {
        border-color: rgba(0, 135, 90, 0.22) !important;
        box-shadow: 0 12px 40px 0 rgba(0, 135, 90, 0.06) !important;
        transform: translateY(-2px) !important;
    }
    
    /* Metric styling inside glass cards */
    .metric-value {
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        font-family: 'Outfit', sans-serif !important;
        margin-top: 4px !important;
        letter-spacing: -0.5px !important;
    }
    .metric-label {
        font-size: 0.8rem !important;
        color: #486352 !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        font-weight: 700 !important;
    }
    
    /* Chat bubbles matching modern messaging UI */
    .chat-bubble {
        padding: 14px 18px !important;
        border-radius: 18px !important;
        margin-bottom: 12px !important;
        max-width: 80% !important;
        line-height: 1.6 !important;
        font-size: 0.95rem !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.01) !important;
    }
    .user-bubble {
        background: linear-gradient(135deg, #00875A, #00a870) !important;
        color: white !important;
        margin-left: auto !important;
        border-bottom-right-radius: 4px !important;
        box-shadow: 0 4px 15px rgba(0, 135, 90, 0.15) !important;
    }
    .agent-bubble {
        background: #ffffff !important;
        color: #1a2c20 !important;
        border: 1px solid rgba(0, 135, 90, 0.08) !important;
        margin-right: auto !important;
        border-bottom-left-radius: 4px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.01) !important;
    }
    
    /* Custom button styling */
    div.stButton > button {
        border-radius: 12px !important;
        border: 1.5px solid #00875A !important;
        background-color: transparent !important;
        color: #00875A !important;
        font-weight: 600 !important;
        padding: 8px 20px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, #00875A, #00a870) !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(0, 135, 90, 0.2) !important;
        transform: translateY(-1px) !important;
    }
    div.stButton > button:active {
        transform: translateY(1px) !important;
    }
    
    /* Style Chat Input Box */
    .stTextInput input {
        background-color: rgba(255, 255, 255, 0.8) !important;
        border: 1px solid rgba(0, 135, 90, 0.12) !important;
        border-radius: 12px !important;
        padding: 12px !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.2s ease !important;
    }
    .stTextInput input:focus {
        border-color: #00875A !important;
        box-shadow: 0 0 0 2px rgba(0, 135, 90, 0.15) !important;
        background-color: #ffffff !important;
    }

    /* Hide Streamlit form helper text (Press Enter to submit form) */
    [data-testid="InputInstructions"], 
    [data-testid="stForm"] [data-testid="stMarkdownContainer"] small,
    [data-testid="stForm"] small,
    [data-testid="stFormSubmitButton"] + div,
    div:has(> [data-testid="stFormSubmitButton"]) + div {
        display: none !important;
    }

    /* Live status green pulse animation */
    @keyframes pulse {
        0% {
            box-shadow: 0 0 0 0 rgba(46, 204, 113, 0.6);
        }
        70% {
            box-shadow: 0 0 0 6px rgba(46, 204, 113, 0);
        }
        100% {
            box-shadow: 0 0 0 0 rgba(46, 204, 113, 0);
        }
    /* Modebar container */
    .modebar-container {
        background: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(8px) !important;
        border-radius: 8px !important;
        border: 1px solid rgba(27, 42, 74, 0.1) !important;
        padding: 2px 4px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    }

    /* Individual buttons */
    .modebar-btn path {
        fill: #1B2A4A !important;   /* dark navy to match app */
    }

    .modebar-btn:hover path {
        fill: #2E7D32 !important;   /* green on hover */
    }

    /* Active button */
    .modebar-btn.active path {
        fill: #2E7D32 !important;
    }
</style>
""", unsafe_allow_html=True)

def section_title(icon, title, subtitle=""):
    sub_html = f"<div style='font-size: 13px; color: #6B7280; font-weight: 400; margin-top: 2px;'>{subtitle}</div>" if subtitle else ""
    st.markdown(f"""
    <div style='margin-bottom: 1.2rem; margin-top: 1.5rem;'>
        <div style='font-size: 18px; font-weight: 700; color: #1B2A4A; display: flex; align-items: center; gap: 8px;'>
            <span>{icon}</span> <span>{title}</span>
        </div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)

# Helper: Load mock data if file does not exist
def seed_mock_data():
    if sheets_handler.use_google:
        return
    if not os.path.exists("family_budget_data.xlsx"):
        try:
            # Put some initial transaction rows for June 2026
            tx_data = [
                {"date": "2026-06-01", "type": "income", "person": "katja", "merchant": "Firma GmbH", "amount": 2800.0, "category": "Einkommen", "subcategory": "Gehalt", "source": "manual", "note": "Monatsgehalt"},
                {"date": "2026-06-01", "type": "income", "person": "dirk", "merchant": "Tech AG", "amount": 3342.50, "category": "Einkommen", "subcategory": "Gehalt", "source": "manual", "note": "Monatsgehalt"},
                {"date": "2026-06-02", "type": "expense", "person": "shared", "merchant": "MietVerwaltung", "amount": 1100.0, "category": "Wohnen", "subcategory": "Miete", "source": "manual"},
                {"date": "2026-06-03", "type": "expense", "person": "shared", "merchant": "Stadtwerke", "amount": 180.0, "category": "Energie", "subcategory": "Strom/Gas", "source": "manual"},
                {"date": "2026-06-05", "type": "expense", "person": "shared", "merchant": "Lidl", "amount": 84.30, "category": "Lebensmittel", "subcategory": "Supermarkt", "source": "manual"},
                {"date": "2026-06-08", "type": "expense", "person": "shared", "merchant": "dm drogerie", "amount": 24.15, "category": "Drogerie", "subcategory": "Drogeriebedarf", "source": "manual"},
                {"date": "2026-06-10", "type": "expense", "person": "shared", "merchant": "HEM Tankstelle", "amount": 75.0, "category": "Benzin", "subcategory": "Tanken", "source": "manual"},
                {"date": "2026-06-12", "type": "expense", "person": "shared", "merchant": "Netflix", "amount": 17.99, "category": "Medien / Streaming", "subcategory": "Streaming", "source": "manual"},
                {"date": "2026-06-15", "type": "expense", "person": "shared", "merchant": "Rewe", "amount": 42.10, "category": "Lebensmittel", "subcategory": "Supermarkt", "source": "manual"},
                {"date": "2026-06-20", "type": "savings", "person": "katja", "merchant": "Trade Republic", "amount": 300.0, "category": "Investitionen (Sparpläne)", "subcategory": "ETF", "source": "manual"},
                {"date": "2026-06-20", "type": "savings", "person": "dirk", "merchant": "Allianz", "amount": 200.0, "category": "Altersvorsorge", "subcategory": "Rente", "source": "manual"}
            ]
            for tx in tx_data:
                sheets_handler.add_transaction(tx)
                
            # Put some initial data for May 2026
            tx_data_may = [
                {"date": "2026-05-01", "type": "income", "person": "katja", "merchant": "Firma GmbH", "amount": 2800.0, "category": "Einkommen", "subcategory": "Gehalt", "source": "manual"},
                {"date": "2026-05-01", "type": "income", "person": "dirk", "merchant": "Tech AG", "amount": 3342.50, "category": "Einkommen", "subcategory": "Gehalt", "source": "manual"},
                {"date": "2026-05-02", "type": "expense", "person": "shared", "merchant": "MietVerwaltung", "amount": 1100.0, "category": "Wohnen", "subcategory": "Miete", "source": "manual"},
                {"date": "2026-05-05", "type": "expense", "person": "shared", "merchant": "Lidl", "amount": 91.50, "category": "Lebensmittel", "subcategory": "Supermarkt", "source": "manual"},
                {"date": "2026-05-08", "type": "expense", "person": "shared", "merchant": "dm drogerie", "amount": 32.80, "category": "Drogerie", "subcategory": "Drogeriebedarf", "source": "manual"},
                {"date": "2026-05-10", "type": "expense", "person": "shared", "merchant": "HEM Tankstelle", "amount": 73.50, "category": "Benzin", "subcategory": "Tanken", "source": "manual"},
                {"date": "2026-05-15", "type": "expense", "person": "shared", "merchant": "Pizzeria Napoli", "amount": 42.00, "category": "Restaurant / Café", "subcategory": "Essen gehen", "source": "manual"}
            ]
            for tx in tx_data_may:
                sheets_handler.add_transaction(tx)
        except Exception as e:
            logger.error(f"Failed to seed mock data: {e}")

seed_mock_data()

# Initialize session state variables
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "agent", "text": "Hallo! Ich bin dein **FamilyBudget AI Assistant**. Wie kann ich dir heute helfen?"}
    ]
if "pending_tx" not in st.session_state:
    st.session_state.pending_tx = None
if "waiting_for" not in st.session_state:
    st.session_state.waiting_for = None
if "pending_correction" not in st.session_state:
    st.session_state.pending_correction = None
if "pending_pdf_txs" not in st.session_state:
    st.session_state.pending_pdf_txs = []
if "menu_selection" not in st.session_state:
    st.session_state.menu_selection = "💬 Chat Assistent"

# --- Google Sheets Active Verification check ---
is_sheet_accessible = False
sheet_error_detail = None
if sheets_handler.use_google:
    try:
        sheets_handler.service.spreadsheets().get(spreadsheetId=sheets_handler.spreadsheet_id).execute()
        is_sheet_accessible = True
    except Exception as e:
        sheet_error_detail = str(e)
        is_sheet_accessible = False

# --- Sidebar Navigation & User Info ---
st.sidebar.markdown("""
<div style='text-align: left; margin-bottom: 16px; margin-top: 5px; padding-left: 2px;'>
    <div style='font-size: 1.6rem; margin-bottom: 4px;'>💰</div>
    <div class='sidebar-logo-title'>FamilyBudget.ai</div>
    <div style='font-size: 0.65rem; color: #5C7F67; letter-spacing: 1.5px; text-transform: uppercase; font-weight: 700; margin-top: 4px;'>FINANZASSISTENT</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<hr style='border:none; border-top:1px solid rgba(255,255,255,0.08); margin:14px 0;'>", unsafe_allow_html=True)

st.sidebar.markdown("<p style='font-size:11px; color:#5C7F67; letter-spacing:0.12em; font-weight:700; margin-bottom:6px; text-transform:uppercase;'>KONTO</p>", unsafe_allow_html=True)

# Initialize current_user in session state if not present
if "current_user" not in st.session_state:
    st.session_state.current_user = "katja"

# Render two togglable buttons side-by-side instead of a selectbox dropdown
col_u1, col_u2 = st.sidebar.columns(2)
with col_u1:
    if st.button("🙋‍♀️ Katja", key="btn_user_katja", use_container_width=True, 
                 type="primary" if st.session_state.current_user == "katja" else "secondary"):
        st.session_state.current_user = "katja"
        st.rerun()
with col_u2:
    if st.button("🙋‍♂️ Dirk", key="btn_user_dirk", use_container_width=True, 
                 type="primary" if st.session_state.current_user == "dirk" else "secondary"):
        st.session_state.current_user = "dirk"
        st.rerun()

current_user = "Katja" if st.session_state.current_user == "katja" else "Dirk"
user_initial = current_user[0].upper()

st.sidebar.markdown(f"""
<div style='background: rgba(255, 255, 255, 0.04); border-radius: 10px; padding: 8px 12px; display: flex; align-items: center; gap: 12px; margin-bottom: 6px;'>
    <div style='background: #00E676; color: #041F10; width: 30px; height: 30px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-family: "Outfit", sans-serif; font-size: 0.95rem;'>
        {user_initial}
    </div>
    <div>
        <div style='font-size: 0.62rem; color: #5C7F67; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 700;'>AKTIVER ACCOUNT</div>
        <div style='font-size: 0.95rem; font-weight: 700; color: #ffffff; font-family: "Outfit", sans-serif;'>{current_user}</div>
    </div>
</div>
""", unsafe_allow_html=True)

import datetime
month_names_de = {1: "Januar", 2: "Februar", 3: "März", 4: "April", 5: "Mai", 6: "Juni", 7: "Juli", 8: "August", 9: "September", 10: "Oktober", 11: "November", 12: "Dezember"}
now_dt = datetime.date.today()
current_month_str_de = f"{month_names_de.get(now_dt.month, now_dt.strftime('%B'))} {now_dt.year}"

st.sidebar.markdown(f"""
<div style='background: rgba(255, 255, 255, 0.04); border-radius: 10px; padding: 8px 12px; margin-bottom: 16px;'>
    <div style='font-size: 0.72rem; color: #5C7F67; font-weight: 500; margin-bottom: 2px;'>Aktueller Monat</div>
    <div style='color:#00E676; font-weight:700; font-size:0.95rem; font-family: "Outfit", sans-serif;'>{current_month_str_de}</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<p style='font-size:11px; color:#5C7F67; letter-spacing:0.12em; font-weight:700; margin-bottom:6px; text-transform:uppercase;'>MENÜ</p>", unsafe_allow_html=True)

MENU_OPTIONS = ["💬 Chat Assistent", "📊 Auswertungen", "📄 Dokumenten-Upload", "⚙️ Einstellungen"]

if "sidebar_radio" in st.session_state and st.session_state.sidebar_radio != st.session_state.menu_selection:
    st.session_state.menu_selection = st.session_state.sidebar_radio

try:
    default_menu_idx = MENU_OPTIONS.index(st.session_state.menu_selection)
except ValueError:
    default_menu_idx = 0

menu = st.sidebar.radio(
    "MENÜ",
    MENU_OPTIONS,
    index=default_menu_idx,
    key="sidebar_radio"
)
st.session_state.menu_selection = menu

st.sidebar.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
if sheets_handler.use_google:
    if is_sheet_accessible:
        status_color = "#00E676"
        status_text = "Verbunden"
        status_icon = "●"
    else:
        status_color = "#EF5350"
        status_text = "Fehler"
        status_icon = "○"
    sheets_label = f"Google Sheets · {status_text}"
else:
    status_color = "#F1C40F"
    status_text = "Lokaler Modus (Excel)"
    status_icon = "●"
    sheets_label = status_text

st.sidebar.markdown(f"""
<div style='padding-top: 12px; margin-top: 12px;'>
    <span style='color:{status_color}; font-size:10px;'>{status_icon}</span>
    <span style='color:#5C7F67; font-size:11px;'> {sheets_label}</span>
</div>
""", unsafe_allow_html=True)

# Show detailed fallback reason in sidebar if sheets connection was unsuccessful
if not sheets_handler.use_google and getattr(sheets_handler, "connection_error", None):
    st.sidebar.markdown(f"""
    <div style='font-size: 9.5px; color: #EF5350; padding-left: 10px; margin-top: -4px; line-height: 1.2;'>
        ⚠️ {sheets_handler.connection_error}
    </div>
    """, unsafe_allow_html=True)

# --- Content Sections ---

if menu == "💬 Chat Assistent":
    # Hero Banner: display only on initial Chat page landing before user interacts
    if os.path.exists("banner.png") and len(st.session_state.get("chat_history", [])) <= 1:
        st.markdown("""
            <div style="border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.12); margin-bottom: 2rem;">
        """, unsafe_allow_html=True)
        st.image("banner.png", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("## 💬 Chat Assistent")
    st.write("Verwalte dein Familienbudget im Gespräch. Trage Ausgaben per Text ein, korrigiere Buchungen oder frage nach Analysen.")

    def process_and_check_transaction(tx):
        # Map default person if unassigned
        if tx.get("type") in ["income", "savings"] and tx.get("person") == "unknown":
            tx["person"] = st.session_state.get("current_user", "shared")

        # Check merchant
        if not tx.get("merchant_specified") or tx.get("merchant", "Unbekannt") == "Unbekannt":
            st.session_state.pending_tx = tx
            st.session_state.waiting_for = "merchant"
            st.session_state.chat_history.append({
                "role": "agent",
                "text": "❓ Für welchen Händler oder welche Quelle soll ich diese Buchung eintragen? (Antworte im Chat oder gib 'abbrechen' ein)"
            })
            st.rerun()

        # Check amount
        if not tx.get("amount_specified") or tx.get("amount", 0.0) <= 0.0:
            st.session_state.pending_tx = tx
            st.session_state.waiting_for = "amount"
            st.session_state.chat_history.append({
                "role": "agent",
                "text": f"❓ Wie hoch war der Betrag bei **{tx['merchant']}**? (Antworte im Chat oder gib 'abbrechen' ein)"
            })
            st.rerun()

        # Check date/month
        if not tx.get("date_specified"):
            st.session_state.pending_tx = tx
            st.session_state.waiting_for = "date"
            st.session_state.chat_history.append({
                "role": "agent",
                "text": f"📅 Für welchen Monat (z.B. Mai) oder welches Datum soll ich die Buchung für **{tx['merchant']}** über **{tx['amount']:.2f} €** eintragen?\n"
                        f"*(Antworte im Chat oder gib 'abbrechen' ein. Standard ist heute: {tx['date']})*"
            })
            st.rerun()

        # Check if category is specified or needs confirmation
        is_cat_unclear = tx.get("confidence", 1.0) < 0.8 or tx.get("category", "Unbekannt") == "Unbekannt"
        
        if is_cat_unclear and st.session_state.waiting_for != "category":
            # Run classification first to see if we can get a suggestion
            with st.spinner("Klassifiziere Kategorie..."):
                classification = classify_transaction(
                    tx.get("merchant"), 
                    tx.get("amount"), 
                    category_hint=tx.get("category_hint"),
                    tx_type=tx.get("type")
                )
                tx["category"] = classification["category"]
                tx["subcategory"] = classification["subcategory"]
                tx["confidence"] = classification["confidence"]
            
            # Re-check after classification
            if tx["confidence"] < 0.8 or tx["category"] == "Unbekannt":
                st.session_state.pending_tx = tx
                st.session_state.waiting_for = "category"
                confirm_prompt = f"❓ Ich habe Folgendes erkannt:\n\n" \
                                 f"**Händler/Quelle:** {tx['merchant']}\n" \
                                 f"**Betrag:** {tx['amount']:.2f} €\n" \
                                 f"**Datum:** {tx['date']}\n" \
                                 f"**Kategorie:** {tx['category']} (Sicherheit: {tx['confidence']:.2f})\n\n" \
                                 f"Bitte bestätige die Kategorie oder wähle eine andere aus:"
                st.session_state.chat_history.append({
                    "role": "agent", 
                    "text": confirm_prompt,
                    "needs_confirmation": True
                })
                st.rerun()

        # High confidence or explicitly specified/confirmed category -> save directly
        with st.spinner("Transaktion wird gespeichert..."):
            res_msg = write_to_sheets(tx)
        st.session_state.chat_history.append({"role": "agent", "text": res_msg})
        st.session_state.pending_tx = None
        st.session_state.waiting_for = None
        st.rerun()

    # 1. Render Chat History
    chat_container = st.container()
    with chat_container:
        for idx, chat in enumerate(st.session_state.chat_history):
            role_class = "user-bubble" if chat["role"] == "user" else "agent-bubble"
            st.markdown(f'<div class="chat-bubble {role_class}">{chat["text"]}</div>', unsafe_allow_html=True)
            
            # Render interactive elements for the last agent message
            if idx == len(st.session_state.chat_history) - 1:
                # Scenario A: Category Confirmation for a pending transaction
                if st.session_state.pending_tx and chat.get("needs_confirmation"):
                    tx = st.session_state.pending_tx
                    st.write("---")
                    st.warning(f"Kategoriebestätigung erforderlich für: **{tx['merchant']}** | **{tx['amount']:.2f} €**")
                    
                    # Add Date / Month editor to allow changing the month/date
                    parsed_date = datetime.strptime(tx.get("date", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d")
                    cols_date = st.columns(2)
                    with cols_date[0]:
                        new_date = st.date_input("Datum / Monat für Buchung anpassen:", value=parsed_date)
                        tx["date"] = new_date.strftime("%Y-%m-%d")
                    
                    # Determine appropriate options
                    tx_type = tx.get("type", "expense")
                    options = []
                    if tx_type == "expense":
                        options = CATEGORIES["expense"]["Variable Kosten"] + CATEGORIES["expense"]["Fixkosten"]
                    elif tx_type == "income":
                        options = CATEGORIES["income"]["Einnahmen"]
                    elif tx_type == "savings":
                        options = CATEGORIES["savings"]["Ersparnisse"]
                    
                    # Highlight recommendation if classifier found one
                    suggested = tx.get("category", "Unbekannt")
                    
                    cols = st.columns(4)
                    for c_idx, opt in enumerate(options[:12]):  # Limit display buttons
                        with cols[c_idx % 4]:
                            label = f"⭐ {opt}" if opt == suggested else opt
                            if st.button(label, key=f"confirm_btn_{c_idx}"):
                                # Save transaction with selected category
                                tx["category"] = opt
                                tx["subcategory"] = "-"
                                # Show spinner while writing to sheets
                                with st.spinner("Schreibe in Google Sheets..."):
                                    res_msg = write_to_sheets(tx)
                                st.session_state.chat_history.append({"role": "agent", "text": res_msg})
                                st.session_state.pending_tx = None
                                st.session_state.waiting_for = None
                                st.rerun()

                # Scenario B: Disambiguation for correction
                if st.session_state.pending_correction and chat.get("needs_disambiguation"):
                    disambig = st.session_state.pending_correction
                    st.write("---")
                    st.info("Bitte wähle die zu korrigierende Buchung aus:")
                    cols = st.columns(len(disambig["matches"]))
                    for m_idx, match in enumerate(disambig["matches"]):
                        with cols[m_idx]:
                            btn_label = f"{match['merchant']} ({match['amount']:.2f} € am {match['date']})"
                            if st.button(btn_label, key=f"disambig_btn_{m_idx}"):
                                # Run update
                                success = sheets_handler.update_transaction(
                                    match["date"], match["merchant"], match["amount"], disambig["new_category"]
                                )
                                if success:
                                    success_msg = f"✅ Korrigiert:\n**{match['merchant']}** | {match['date']} | {match['amount']:.2f} € → Kategorie geändert zu **{disambig['new_category']}**"
                                    st.session_state.chat_history.append({"role": "agent", "text": success_msg})
                                else:
                                    st.session_state.chat_history.append({"role": "agent", "text": "❌ Fehler beim Aktualisieren der Zeile."})
                                st.session_state.pending_correction = None
                                st.rerun()

    # Render quick action template options if chat history has just the greeting
    if len(st.session_state.chat_history) == 1:
        st.write("")
        st.markdown("<p style='font-size: 0.75rem; font-weight: 700; color: #486352; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;'>Schnell-Aktionen:</p>", unsafe_allow_html=True)
        cols_quick = st.columns(3)
        quick_actions = [
            ("📝 Lidl 14,50 €", "Heute 14.50 € bei Lidl ausgegeben"),
            ("📊 Juni Auswertung", "Zeige mir die Auswertung für Juni 2026"),
            ("💡 Budget abfragen", "Wie steht mein Budget für diesen Monat?")
        ]
        for q_idx, (label, cmd_text) in enumerate(quick_actions):
            with cols_quick[q_idx]:
                if st.button(label, key=f"quick_act_{q_idx}", use_container_width=True):
                    st.session_state.run_chat_query = cmd_text
                    st.session_state.chat_history.append({"role": "user", "text": cmd_text})
                    st.rerun()

    # 2. Chat Input Form
    st.write("")
    with st.form("chat_form", clear_on_submit=True):
        chat_cols = st.columns([8.5, 1.5])
        with chat_cols[0]:
            user_input = st.text_input(
                "Nachricht eingeben...", 
                placeholder="z.B. 'Heute 23,50 € bei Lidl ausgegeben'...", 
                label_visibility="collapsed"
            )
        with chat_cols[1]:
            submitted = st.form_submit_button("Senden", use_container_width=True)

    # 3. Handle Message Processing
    query_text = ""
    if submitted and user_input.strip():
        query_text = user_input.strip()
        st.session_state.chat_history.append({"role": "user", "text": query_text})
    elif "run_chat_query" in st.session_state:
        query_text = st.session_state.pop("run_chat_query")

    if query_text:
        user_input_lower = query_text.lower().strip()
        
        # Check intents to allow aborting/canceling or jumping to correction/analytics
        is_cancel = user_input_lower in ["abbrechen", "cancel", "stop", "nein", "stornieren"]
        is_correction = "korrigiere" in user_input_lower or "korrektur" in user_input_lower or "war keine" in user_input_lower or "änder" in user_input_lower
        is_analytics = "auswertung" in user_input_lower or "analyse" in user_input_lower or "trends" in user_input_lower

        try:
            if is_cancel:
                st.session_state.pending_tx = None
                st.session_state.waiting_for = None
                st.session_state.chat_history.append({
                    "role": "agent",
                    "text": "Vorgang abgebrochen. Wie kann ich dir sonst helfen?"
                })
                st.rerun()

            elif is_correction:
                st.session_state.pending_tx = None
                st.session_state.waiting_for = None
                with st.spinner("Korrektur wird im Sheet gesucht..."):
                    result = correct_transaction(query_text)
                
                if result["status"] == "success":
                    st.session_state.chat_history.append({"role": "agent", "text": result["message"]})
                elif result["status"] == "disambiguate":
                    st.session_state.pending_correction = {
                        "matches": result["matches"],
                        "new_category": result["new_category"]
                    }
                    st.session_state.chat_history.append({
                        "role": "agent", 
                        "text": result["message"],
                        "needs_disambiguation": True
                    })
                else:
                    st.session_state.chat_history.append({"role": "agent", "text": result["message"]})
                st.rerun()

            elif is_analytics:
                st.session_state.pending_tx = None
                st.session_state.waiting_for = None
                # Parse month if present (e.g. "Juni", "06", "2026-06")
                target_month = None
                months_mapping = {
                    "jan": "01", "feb": "02", "mär": "03", "apr": "04", "mai": "05", "jun": "06",
                    "jul": "07", "aug": "08", "sep": "09", "okt": "10", "nov": "11", "dez": "12"
                }
                for de_m, m_num in months_mapping.items():
                    if de_m in user_input_lower:
                        target_month = f"2026-{m_num}"
                        break
                
                with st.spinner("Monatsanalyse wird berechnet..."):
                    summary_text, _ = generate_analytics(target_month)
                st.session_state.chat_history.append({"role": "agent", "text": summary_text})
                st.rerun()

            # Active Clarification response flow
            elif st.session_state.pending_tx and st.session_state.waiting_for:
                with st.spinner("Verarbeite deine Antwort..."):
                    updated_tx = clarify_pending_transaction(st.session_state.pending_tx, query_text)
                    st.session_state.pending_tx = updated_tx
                process_and_check_transaction(updated_tx)

            # Normal parsing flow
            else:
                with st.spinner("Finanzdaten werden analysiert..."):
                    tx = parse_text(query_text)
                
                if tx.get("is_transaction"):
                    process_and_check_transaction(tx)
                else:
                    # General conversation/greeting
                    with st.spinner("Antwort wird generiert..."):
                        gen_resp = generate_general_response(query_text)
                    st.session_state.chat_history.append({"role": "agent", "text": gen_resp})
                    st.rerun()

        except Exception as err:
            logger.error("Error in chat processing", exc_info=True)
            friendly_err = get_friendly_error_message(err)
            st.session_state.chat_history.append({
                "role": "agent",
                "text": f"❌ Fehler bei der Verarbeitung: {friendly_err}"
            })
            st.rerun()

elif menu == "📊 Auswertungen":
    st.markdown("## 📊 Auswertungen")
    st.write("Analysiere das Familienbudget. Vergleiche Einnahmen, Ausgaben und Ersparnisse im Jahresverlauf oder im Detail.")
    
    try:
        # Check if cached analytics results exist and data is not dirty
        if "analytics_results" not in st.session_state or st.session_state.get("analytics_dirty", True):
            with st.spinner("Berechne Auswertungen aus den Daten..."):
                sheet_names = sheets_handler.get_all_sheet_names()
                sheet_data = {}
                for name in sheet_names:
                    if "expenses" in name.lower() or "income" in name.lower() or "savings" in name.lower():
                        df = sheets_handler.read_sheet_data(name)
                        sheet_data[name] = df
                        
                from skills.analytics import generate_analytics, write_analytics_to_sheets, GERMAN_MONTHS
                analytics_results = generate_analytics(sheet_data)
                st.session_state.analytics_results = analytics_results
                st.session_state.analytics_dirty = False
                
                # Write back to sheets in try-except
                try:
                    write_analytics_to_sheets(analytics_results)
                except Exception as e:
                    logger.error(f"Error writing analytics back to sheets: {e}")
        else:
            analytics_results = st.session_state.analytics_results
            from skills.analytics import GERMAN_MONTHS
            
        import plotly.graph_objects as go

        # Helper: section title with consistent icon
        def section_title(icon: str, text: str, subtitle: str = ""):
            st.markdown(f"""
                <div style='margin-bottom: 4px;'>
                    <span style='font-size:18px; font-weight:700; color:#1B2A4A;'>
                        {icon}&nbsp;&nbsp;{text}
                    </span>
                </div>
                {"<p style='font-size:13px; color:#6B7280; margin-top:0;'>" + subtitle + "</p>" if subtitle else ""}
            """, unsafe_allow_html=True)

        # Helper: format currency
        def format_currency_de(val: float) -> str:
            sign = "-" if val < 0 else ""
            abs_val = abs(val)
            formatted = f"{abs_val:,.2f}"
            formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
            return f"{sign}€ {formatted}"
            
        def color_bilanz(val):
            color = "#00875a" if val >= 0 else "#d97706"
            return f"color: {color}; font-weight: bold;"

        # --- Section 1: Jahresübersicht ---
        col_hdr1, col_hdr2 = st.columns([7.5, 2.5])
        with col_hdr1:
            section_title("▦", "Jahresübersicht")
        with col_hdr2:
            if st.button("Daten neu laden 🔄", key="ref_analytics_btn", use_container_width=True):
                st.session_state.analytics_dirty = True
                st.rerun()
        
        summary_table_rows = analytics_results["summary_table"]
        
        if not summary_table_rows:
            st.warning("Keine Daten für die Jahresübersicht vorhanden.")
        else:
            df_summary = pd.DataFrame(summary_table_rows)
            if "_month_key" in df_summary.columns:
                df_summary = df_summary.drop(columns=["_month_key"])
                
            df_display = df_summary.copy()
            df_display["Einnahmen"] = df_display["Einnahmen"].apply(format_currency_de)
            df_display["Ausgaben"] = df_display["Ausgaben"].apply(format_currency_de)
            df_display["Ersparnisse"] = df_display["Ersparnisse"].apply(format_currency_de)
            df_display["Bilanz"] = df_display["Bilanz"].apply(format_currency_de)
            
            styled_df = df_display.style.apply(
                lambda x: [color_bilanz(row["Bilanz"]) for row in summary_table_rows],
                axis=0,
                subset=["Bilanz"]
            )
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

        st.markdown("---")

        # --- Section 2: Donut Chart (Full Width) ---
        expenses_by_category = analytics_results["expenses_by_category"]
        current_month_str = analytics_results.get("current_month", "Unbekannt")
        parts = current_month_str.split("-")
        month_name = GERMAN_MONTHS.get(parts[1], parts[1]) if len(parts) > 1 else parts[0]
        year_str = parts[0] if len(parts) > 0 else ""
        current_month_display = f"{month_name} {year_str}".strip()
        
        CHART_COLORS = [
            "#1B2A4A",  # Dark navy   — largest category
            "#2E7D32",  # Deep green  — 2nd
            "#388E3C",  # Forest green — 3rd
            "#43A047",  # Medium green — 4th
            "#66BB6A",  # Fresh green  — 5th
            "#81C784",  # Light green  — 6th
            "#A5D6A7",  # Pale green   — 7th
            "#C8E6C9",  # Very pale    — 8th
            "#B0BEC5",  # Cool gray    — 9th
            "#90A4AE",  # Blue-gray    — 10th
            "#78909C",  # Slate        — 11th
            "#546E7A",  # Dark slate   — 12th
            "#455A64",  # Charcoal     — 13th
            "#37474F",  # Near-black   — 14th
        ]

        BAR_COLORS = {
            "Einnahmen":   "#2E7D32",  # Deep green
            "Ausgaben":    "#1B2A4A",  # Dark navy
            "Ersparnisse": "#81C784",  # Light green
        }

        section_title("◉", "Ausgaben nach Kategorie", f"Kategorieaufteilung für {current_month_display}")
        if not expenses_by_category:
            st.info(f"Keine Ausgaben in der Kategorie für {current_month_display} vorhanden.")
        else:
            sorted_exp = sorted(expenses_by_category.items(), key=lambda x: x[1], reverse=True)
            labels = [k for k, v in sorted_exp]
            values = [v for k, v in sorted_exp]
            total_val = sum(values) if sum(values) > 0 else 1.0
            
            legend_labels = [f"{lbl} ({format_currency_de(val)})" for lbl, val in zip(labels, values)]
            slice_colors = [CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(values))]
            text_templates = ["%{percent:.1%}" if (v / total_val) >= 0.03 else "" for v in values]
            
            fig_pie = go.Figure(data=[go.Pie(
                labels=legend_labels,
                values=values,
                hole=0.45,
                textposition='inside',
                textinfo='percent',
                texttemplate=text_templates,
                textfont=dict(size=11, color="white"),
                insidetextorientation="auto",
                marker=dict(colors=slice_colors),
                hovertemplate="<b>%{label}</b><br>Betrag: %{value:,.2f} €<br>Anteil: %{percent}<extra></extra>"
            )])
            fig_pie.update_layout(
                height=420,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#1B2A4A", family="Inter, Helvetica, sans-serif", size=13),
                margin=dict(t=20, b=20, l=20, r=20),
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.02,
                    bgcolor="rgba(0,0,0,0)",
                    borderwidth=0,
                    font=dict(color="#1B2A4A", size=12),
                ),
            )
            st.plotly_chart(
                fig_pie,
                use_container_width=True,
                config={
                    "displayModeBar": True,
                    "displaylogo": False,
                    "modeBarButtonsToRemove": [
                        "select2d", "lasso2d", "autoScale2d",
                        "hoverClosestCartesian", "hoverCompareCartesian",
                        "toggleSpikelines", "zoom2d", "zoomIn2d", "zoomOut2d",
                    ],
                    "modeBarButtonsToAdd": [],
                    "toImageButtonOptions": {
                        "format": "png",
                        "filename": "ausgaben_kategorien",
                        "scale": 2,
                    },
                }
            )

        st.markdown("<div style='margin: 1.5rem 0'></div>", unsafe_allow_html=True)
        st.markdown("---")

        # --- Section 3: Bar Chart (Full Width) ---
        section_title("↗", "Monatsverlauf", "Einnahmen, Ausgaben & Ersparnisse im Vergleich")
        if not summary_table_rows:
            st.info("Keine Verlaufsdaten für das Bar-Chart vorhanden.")
        else:
            ALL_MONTHS = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
            row_by_m = {}
            for row in summary_table_rows:
                m_key = row.get("_month_key", "")
                if m_key and "-" in m_key:
                    try:
                        m_idx = int(m_key.split("-")[1])
                        row_by_m[m_idx] = row
                    except ValueError:
                        pass
                else:
                    for idx_m, (m_num_str, m_full_name) in enumerate(GERMAN_MONTHS.items(), start=1):
                        if m_full_name.lower() == row.get("Monat", "").lower():
                            row_by_m[idx_m] = row
                            break

            months_list = ALL_MONTHS
            incomes = [float(row_by_m.get(i, {}).get("Einnahmen", 0.0)) for i in range(1, 13)]
            expenses = [float(row_by_m.get(i, {}).get("Ausgaben", 0.0)) for i in range(1, 13)]
            savings = [float(row_by_m.get(i, {}).get("Ersparnisse", 0.0)) for i in range(1, 13)]
            
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                x=months_list,
                y=incomes,
                name="Einnahmen",
                marker_color=BAR_COLORS["Einnahmen"],
                offsetgroup=0,
                text=[f"<b>€ {int(round(v)):,}".replace(",", ".") + "</b>" if v > 0 else "" for v in incomes],
                textposition="outside",
                constraintext="none",
                textfont=dict(size=14, color="#1B2A4A", family="Inter, Helvetica, sans-serif"),
                cliponaxis=False,
            ))
            fig_bar.add_trace(go.Bar(
                x=months_list,
                y=expenses,
                name="Ausgaben",
                marker_color=BAR_COLORS["Ausgaben"],
                offsetgroup=1,
                text=[f"<b>€ {int(round(v)):,}".replace(",", ".") + "</b>" if v > 0 else "" for v in expenses],
                textposition="outside",
                constraintext="none",
                textfont=dict(size=14, color="#1B2A4A", family="Inter, Helvetica, sans-serif"),
                cliponaxis=False,
            ))
            fig_bar.add_trace(go.Bar(
                x=months_list,
                y=savings,
                name="Ersparnisse",
                marker_color=BAR_COLORS["Ersparnisse"],
                offsetgroup=2,
                text=[f"<b>€ {int(round(v)):,}".replace(",", ".") + "</b>" if v > 0 else "" for v in savings],
                textposition="outside",
                constraintext="none",
                textfont=dict(size=14, color="#1B2A4A", family="Inter, Helvetica, sans-serif"),
                cliponaxis=False,
            ))
            
            import datetime
            try:
                curr_m_str = analytics_results.get("current_month", datetime.date.today().strftime("%Y-%m"))
                current_month_idx = int(curr_m_str.split("-")[1])
            except Exception:
                current_month_idx = datetime.date.today().month

            start_idx = max(0, current_month_idx - 3)
            end_idx = min(11, current_month_idx + 2)
            
            fig_bar.update_layout(
                width=1400,
                height=420,
                dragmode="pan",
                barmode="group",
                bargap=0.25,
                bargroupgap=0.08,
                uniformtext=dict(minsize=14, mode='show'),
                xaxis=dict(
                    title=None, 
                    tickfont=dict(size=12, color="#1B2A4A"), 
                    fixedrange=False,
                    range=[start_idx - 0.5, end_idx + 0.5]
                ),
                yaxis=dict(
                    title="Betrag in €", 
                    tickfont=dict(color="#1B2A4A"), 
                    gridcolor="rgba(0,0,0,0.06)",
                    fixedrange=True
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#1B2A4A", family="Inter, Helvetica, sans-serif", size=13),
                margin=dict(t=70, b=80, l=60, r=40),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.18,
                    xanchor="center",
                    x=0.5,
                    bgcolor="rgba(0,0,0,0)",
                    borderwidth=0,
                    font=dict(color="#1B2A4A", size=12),
                ),
            )
            st.plotly_chart(
                fig_bar,
                use_container_width=False,
                config={
                    "scrollZoom": False,
                    "displayModeBar": True,
                    "displaylogo": False,
                    "modeBarButtonsToRemove": [
                        "select2d", "lasso2d", "autoScale2d",
                        "hoverClosestCartesian", "hoverCompareCartesian",
                        "toggleSpikelines", "zoom2d", "zoomIn2d", "zoomOut2d",
                    ],
                    "modeBarButtonsToAdd": [],
                    "toImageButtonOptions": {
                        "format": "png",
                        "filename": "monatsverlauf",
                        "scale": 2,
                    },
                }
            )

        st.markdown("---")

        # --- Section 4: Month-over-Month Category Comparison ---
        section_title("⇄", "Vergleich: Aktueller Monat vs. Vormonat")
        
        mom_comparison = analytics_results["mom_comparison"]
        
        if not mom_comparison:
            st.info("Keine Daten für den Vergleich vorhanden.")
        else:
            categories = list(mom_comparison.keys())
            cols = st.columns(4)
            for idx, cat in enumerate(categories):
                data = mom_comparison[cat]
                curr_val = data["current"]
                prev_val = data["previous"]
                
                if prev_val == 0:
                    delta_text = "Kein Vormonat"
                    delta_color = "#9CA3AF"   # neutral gray
                    icon_sym = "●"
                else:
                    pct = ((curr_val - prev_val) / prev_val) * 100
                    if pct > 0:
                        delta_text = f"+{pct:.1f}%"
                        delta_color = "#DC2626"   # red — spending went up
                        icon_sym = "▲"
                    elif pct < 0:
                        delta_text = f"{pct:.1f}%"
                        delta_color = "#16A34A"   # green — spending went down
                        icon_sym = "▼"
                    else:
                        delta_text = "±0%"
                        delta_color = "#6B7280"
                        icon_sym = "●"
                    
                with cols[idx % 4]:
                    card_html = f"""
                    <div style="background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); border: 1px solid rgba(0, 135, 90, 0.15); border-radius: 16px; padding: 16px; margin-bottom: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); min-height: 135px;">
                        <div title="{cat}" style="font-size: 0.78rem; color: #1f3a29; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 700; line-height: 1.2; min-height: 2.2rem; display: flex; align-items: center; word-break: break-word;">
                            {cat}
                        </div>
                        <div style="font-size: 1.5rem; font-weight: 800; color: #0b1a11; margin-top: 6px; font-family: 'Outfit', sans-serif;">
                            {format_currency_de(curr_val)}
                        </div>
                        <div style="font-size: 0.8rem; margin-top: 6px; font-weight: 600; color: {delta_color};">
                            {icon_sym} {delta_text} <br><span style="color: #3b5243;">vs. Vormonat ({format_currency_de(prev_val)})</span>
                        </div>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)
                    
    except Exception as e:
        logger.error(f"Error loading analytics data: {e}", exc_info=True)
        st.error("❌ Daten konnten nicht geladen werden. Bitte Google Sheets Verbindung prüfen.")
        if st.button("Zu den Einstellungen gehen ⚙️", key="err_go_to_settings"):
            st.session_state.menu_selection = "⚙️ Einstellungen"
            st.rerun()


elif menu == "📄 Dokumenten-Upload":
    st.markdown("## 📄 Dokumenten-Upload (PDF / Bild)")
    st.write("Lade deinen Bank-Kontoauszug als PDF oder einen Screenshot/ein Bild deiner Einnahmen/Ersparnisse hoch. Der Assistent extrahiert alle Buchungen automatisch.")
    
    uploaded_file = st.file_uploader("Datei auswählen (PDF, PNG, JPG, JPEG)...", type=["pdf", "png", "jpg", "jpeg"])
    
    st.write("")
    st.markdown("#### Optionaler Kommentar")
    user_comment = st.text_area(
        label="Hinweis für den Assistenten (optional)",
        placeholder=(
            "z. B. 'Das ist der Kontoauszug für Mai 2026.' "
            "oder 'Die Überweisung über 200 € ist Miete, nicht Freizeit.' "
            "oder 'Buchungen von SANDERS sind immer Bäckerei.'"
        ),
        height=100,
        max_chars=500,
        help="Dein Hinweis wird direkt an den Assistenten weitergegeben und hilft bei der korrekten Kategorisierung.",
    )
    
    if uploaded_file is not None:
        file_ext = uploaded_file.name.split(".")[-1].lower()
        is_pdf = file_ext == "pdf"
        
        button_label = "Dokument analysieren"
        
        if st.button(button_label):
            spinner_msg = "Analysiere PDF-Inhalt mit pdfplumber + Gemini..." if is_pdf else "Analysiere Bild-Inhalt mit Gemini Vision..."
            with st.spinner(spinner_msg):
                try:
                    file_bytes = uploaded_file.read()
                    if is_pdf:
                        parsed_txs = parse_pdf(file_bytes, context=user_comment)
                    else:
                        mime_type = f"image/{file_ext}" if file_ext in ["png", "gif"] else "image/jpeg"
                        parsed_txs = parse_image(file_bytes, mime_type, context=user_comment)
                        
                    if not parsed_txs:
                        st.error("Es konnten keine Buchungen im Dokument identifiziert werden.")
                    else:
                        for i, tx in enumerate(parsed_txs):
                            tx["id"] = f"tx_{i}"
                        st.session_state.pending_pdf_txs = parsed_txs
                        if user_comment and user_comment.strip():
                            st.session_state.last_doc_comment = user_comment.strip()
                        else:
                            st.session_state.last_doc_comment = None
                        st.success(f"Erfolgreich {len(parsed_txs)} Buchungen identifiziert! Bitte überprüfe die Kategorisierungen unten.")
                except Exception as e:
                    st.error(f"Fehler bei der Dokumentenverarbeitung: {e}")

    # Render review dashboard if there are pending transactions
    if st.session_state.pending_pdf_txs:
        st.markdown("### 🔍 Transaktionsprüfung")
        if st.session_state.get("last_doc_comment"):
            st.info(f"ℹ️ Dein Hinweis wurde berücksichtigt: „{st.session_state.last_doc_comment}“")
        st.info("Markierte Buchungen (⚠️) benötigen eine manuelle Bestätigung. Du kannst die Kategorien und Zuordnungen direkt anpassen.")
        
        updated_txs = []
        
        for idx, tx in enumerate(st.session_state.pending_pdf_txs):
            confidence = tx.get("confidence", 1.0)
            is_low_conf = confidence < 0.8 or tx.get("category") == "Unbekannt"
            
            # Outer styled container with 6 columns
            col1, col2, col3, col4, col5, col6 = st.columns([1.0, 2.3, 1.2, 2.5, 1.8, 0.7])
            
            with col1:
                st.write(tx.get("date"))
            with col2:
                warning_label = "⚠️ " if is_low_conf else "✅ "
                st.write(f"{warning_label}**{tx.get('merchant')}**")
            with col3:
                sign = "+" if tx.get("type") in ["income"] else "-"
                color = "#00875a" if tx.get("type") in ["income"] else "#e6b800" if tx.get("type") in ["expense"] else "#52b788"
                st.markdown(f"<span style='color:{color}; font-weight: 600;'>{sign} {tx.get('amount'):.2f} €</span>", unsafe_allow_html=True)
            with col4:
                # Dropdown for category
                tx_type = tx.get("type", "expense")
                if tx_type == "expense":
                    categories_list = CATEGORIES["expense"]["Variable Kosten"] + CATEGORIES["expense"]["Fixkosten"]
                elif tx_type == "income":
                    categories_list = CATEGORIES["income"]["Einnahmen"]
                else:
                    categories_list = CATEGORIES["savings"]["Ersparnisse"]
                
                cur_cat = tx.get("category", "Unbekannt")
                if cur_cat not in categories_list:
                    categories_list.append(cur_cat)
                    
                selected_cat = st.selectbox(
                    "Kategorie",
                    categories_list,
                    index=categories_list.index(cur_cat),
                    key=f"pdf_cat_{tx.get('id', idx)}",
                    label_visibility="collapsed"
                )
                tx["category"] = selected_cat
            with col5:
                # Dropdown for person (only relevant for income/savings, expense is shared)
                if tx_type in ["income", "savings"]:
                    raw_pers = tx.get("person", "unknown")
                    if raw_pers.lower() in ["shared", "gemeinsam"]:
                        cur_pers = "Gemeinsam"
                    elif raw_pers.lower() == "unknown":
                        cur_pers = "Unknown"
                    else:
                        cur_pers = raw_pers.capitalize()
                        
                    pers_list = ["Katja", "Dirk", "Gemeinsam"]
                    if cur_pers not in pers_list and cur_pers != "Unknown":
                        pers_list.append(cur_pers)
                    
                    # Map default index cleanly
                    default_idx = 0
                    if cur_pers == "Dirk":
                        default_idx = 1
                    elif cur_pers == "Gemeinsam":
                        default_idx = 2
                        
                    selected_pers = st.selectbox(
                        "Person",
                        pers_list,
                        index=default_idx,
                        key=f"pdf_pers_{tx.get('id', idx)}",
                        label_visibility="collapsed"
                    )
                    tx["person"] = "shared" if selected_pers == "Gemeinsam" else selected_pers.lower()
                else:
                    st.write("Gemeinsam")
            with col6:
                if st.button("🗑️", key=f"del_pdf_tx_{tx.get('id', idx)}"):
                    st.session_state.pending_pdf_txs.remove(tx)
                    st.rerun()
            updated_txs.append(tx)
            st.markdown("<hr style='margin: 8px 0; opacity: 0.1;'>", unsafe_allow_html=True)
            
        st.write("")
        col_actions = st.columns([6, 2, 2])
        with col_actions[1]:
            if st.button("Abbrechen", width="stretch"):
                st.session_state.pending_pdf_txs = []
                st.rerun()
        with col_actions[2]:
            if st.button("In Sheets speichern", type="primary", width="stretch"):
                with st.spinner("Speichere Buchungen..."):
                    try:
                        saved_count = 0
                        for tx in updated_txs:
                            # Write to sheets
                            success = sheets_handler.add_transaction(tx)
                            if success:
                                saved_count += 1
                        
                        st.success(f"Erfolgreich {saved_count} von {len(updated_txs)} Buchungen eingetragen!")
                        st.session_state.pending_pdf_txs = []
                        st.rerun()
                    except Exception as err:
                        friendly_err = get_friendly_error_message(err)
                        st.error(f"⚠️ Fehler beim Speichern der Buchungen: {friendly_err}")


elif menu == "⚙️ Einstellungen":
    st.markdown("## ⚙️ Einstellungen & Setup")
    
    st.write("Hier kannst du API Keys und Google Sheets Verbindungen konfigurieren.")
    
    st.markdown("""
    <div class="glass-card">
        <h3>🔑 API-Schlüssel</h3>
        <p>Die Anwendung liest Schlüssel standardmäßig aus dem Secret Manager oder der lokalen <b>.env</b> Datei.</p>
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    
    with st.expander("Google Sheets API Konfiguration"):
        st.write("Trage deine Service Account Credentials und Spreadsheet ID ein, um das Google Sheet zu aktivieren:")
        
        # Check spreadsheet ID from st.secrets or os.environ
        current_ss_id = ""
        try:
            if "SPREADSHEET_ID" in st.secrets:
                current_ss_id = st.secrets["SPREADSHEET_ID"]
            elif "SPREDSHEET_ID" in st.secrets:
                current_ss_id = st.secrets["SPREDSHEET_ID"]
        except Exception:
            pass
        if not current_ss_id:
            current_ss_id = os.environ.get("SPREADSHEET_ID") or os.environ.get("SPREDSHEET_ID") or ""

        spreadsheet_id_val = st.text_input("Spreadsheet ID", value=current_ss_id)
        
        # Check if GOOGLE_SERVICE_ACCOUNT_JSON is in st.secrets or os.environ
        has_cloud_secret = False
        try:
            if "GOOGLE_SERVICE_ACCOUNT_JSON" in st.secrets:
                has_cloud_secret = True
        except Exception:
            pass
        if "GOOGLE_SERVICE_ACCOUNT_JSON" in os.environ:
            has_cloud_secret = True

        service_account_exists = os.path.exists("service_account.json") or has_cloud_secret
        
        if has_cloud_secret:
            st.write("Google Sheets Verbindung: ✅ Aktiv (Cloud Secret geladen)")
        else:
            st.write(f"Google Sheets Verbindung: {'✅ Service-Account-Datei geladen' if service_account_exists else '❌ Keine Service-Account-Datei (service_account.json) vorhanden'}")
        
        if st.button("Sheets Verbindung aktualisieren"):
            # Update env memory
            os.environ["SPREADSHEET_ID"] = spreadsheet_id_val
            # Reinitialize handler
            from importlib import reload
            import utils.sheets_handler
            reload(utils.sheets_handler)
            st.success("Einstellungen geladen! Bitte lade die App neu, um die Verbindung zu aktivieren.")
            st.rerun()

    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    section_title("≡", "Kategorien verwalten", "Kategorien für Ausgaben, Einnahmen und Ersparnisse")
    
    all_categories_data = load_categories_from_sheets()
    
    tab_exp, tab_inc, tab_sav = st.tabs(["💸 Ausgaben", "💰 Einnahmen", "🏦 Ersparnisse"])
    
    tab_mapping = [
        (tab_exp, "expense", "Ausgaben"),
        (tab_inc, "income", "Einnahmen"),
        (tab_sav, "savings", "Ersparnisse")
    ]
    
    for tab_obj, type_key, type_title in tab_mapping:
        with tab_obj:
            st.write(f"Verwalte Kategorien und automatische Keywords für **{type_title}**:")
            items = all_categories_data.get(type_key, [])
            
            if not items:
                st.info(f"Keine Kategorien für {type_title} vorhanden.")
            else:
                h1, h2, h3 = st.columns([3, 5, 1])
                with h1:
                    st.markdown("<span style='font-size:0.8rem; color:#8da382; font-weight:700; text-transform:uppercase;'>Kategoriename</span>", unsafe_allow_html=True)
                with h2:
                    st.markdown("<span style='font-size:0.8rem; color:#8da382; font-weight:700; text-transform:uppercase;'>Keywords (kommagetrennt)</span>", unsafe_allow_html=True)
                with h3:
                    st.markdown("<span style='font-size:0.8rem; color:#8da382; font-weight:700; text-transform:uppercase;'>Aktion</span>", unsafe_allow_html=True)
                
                st.markdown("<hr style='margin:4px 0 12px 0; opacity:0.2;'>", unsafe_allow_html=True)
                
                for i, cat in enumerate(items):
                    col1, col2, col3 = st.columns([3, 5, 1])
                    with col1:
                        st.markdown(f"<div style='margin-top: 6px;'>**{cat['name']}**</div>", unsafe_allow_html=True)
                    with col2:
                        kw_val = ", ".join(cat.get("keywords", []))
                        new_keywords_input = st.text_input(
                            label="Keywords",
                            value=kw_val,
                            key=f"kw_{type_key}_{i}",
                            label_visibility="collapsed"
                        )
                        clean_kws = [k.strip() for k in new_keywords_input.split(",") if k.strip()]
                        if clean_kws != cat.get("keywords", []):
                            update_category_keywords(type_key, cat["name"], clean_kws)
                            st.rerun()
                            
                    with col3:
                        if st.button("🗑️", key=f"del_{type_key}_{i}", help="Kategorie löschen"):
                            usage_count = count_transactions_with_category(cat["name"])
                            if usage_count > 0:
                                st.warning(f"⚠️ „{cat['name']}“ wird in {usage_count} Buchungen verwendet und kann nicht gelöscht werden. Weise diese Buchungen zuerst einer anderen Kategorie zu.")
                            else:
                                delete_category(type_key, cat["name"])
                                st.success(f"✅ Kategorie „{cat['name']}“ wurde gelöscht.")
                                st.rerun()
                                
            st.markdown("<hr style='margin: 1.5rem 0 1rem 0;'>", unsafe_allow_html=True)
            st.markdown("##### Neue Kategorie hinzufügen")
            
            col1, col2, col3 = st.columns([3, 5, 1])
            with col1:
                new_name = st.text_input("Kategoriename", placeholder="z. B. Haustier", key=f"new_cat_name_{type_key}")
            with col2:
                new_keywords = st.text_input("Keywords (kommagetrennt)", placeholder="z. B. tierarzt,fressnapf,zooplus", key=f"new_cat_keywords_{type_key}")
            with col3:
                st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
                if st.button("＋ Hinzufügen", key=f"add_cat_{type_key}"):
                    if new_name.strip():
                        add_category(
                            type_=type_key,
                            name=new_name.strip(),
                            keywords=[k.strip() for k in new_keywords.split(",") if k.strip()]
                        )
                        st.success(f"✅ Kategorie „{new_name.strip()}“ wurde hinzugefügt.")
                        st.rerun()
                    else:
                        st.warning("⚠️ Bitte einen Kategorienamen eingeben.")
