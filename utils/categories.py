# utils/categories.py

CATEGORIES = {
    "expense": {
        "Fixkosten": [
            "Wohnen",
            "Energie",
            "Kommunikation",
            "Medien / Streaming",
            "Mobilität",
            "Fitness",
            "Versicherungen",
            "Sonstige Fixkosten"
        ],
        "Variable Kosten": [
            "Lebensmittel",
            "Drogerie",
            "Benzin",
            "Auto",
            "Kleidung",
            "Gesundheit",
            "Geschenke",
            "Abonnements/Digital",
            "Freizeit",
            "Restaurant / Café",
            "Transfer",
            "Unbekannt"
        ]
    },
    "income": {
        "Einnahmen": [
            "Einkommen",
            "Dividenden",
            "Zinsen",
            "Cashback",
            "Verkauf",
            "Geschenk (Geld)",
            "Sonstiges"
        ]
    },
    "savings": {
        "Ersparnisse": [
            "Investitionen (Sparpläne)",
            "Altersvorsorge",
            "Zeitwertpapiere"
        ]
    }
}

# Mapping of known keywords/merchants to category, subcategory and confidence
# According to rules:
# Rossmann, dm -> Drogerie (0.99)
# Kaufland, Penny, Lidl, Aldi, Netto, Rewe -> Lebensmittel (0.99)
# Too Good To Go -> Lebensmittel (0.97)
# HEM, Shell, Aral -> Benzin (0.98)
# Netflix, Spotify -> Medien/Streaming (0.97)
# Apple, Google Payment -> Abonnements/Digital (0.95)
# Amazon -> always ask back (Confidence 0.70)
# Überweisungen -> Transfer (0.95)
# Unbekannte Händler -> Unbekannt (< 0.50)
STATIC_RULES = [
    {"pattern": r"rossmann|dm\b|dm drogerie", "category": "Drogerie", "subcategory": "Drogeriebedarf", "confidence": 0.99, "type": "expense"},
    {"pattern": r"kaufland|penny|lidl|aldi|netto|rewe", "category": "Lebensmittel", "subcategory": "Supermarkt", "confidence": 0.99, "type": "expense"},
    {"pattern": r"too good to go|tgtg", "category": "Lebensmittel", "subcategory": "Too Good To Go", "confidence": 0.97, "type": "expense"},
    {"pattern": r"hem|shell|aral|tankstelle|esso|total\b|jet\b", "category": "Benzin", "subcategory": "Tanken", "confidence": 0.98, "type": "expense"},
    {"pattern": r"netflix|spotify|youtube premium|disney|apple music", "category": "Medien / Streaming", "subcategory": "Streaming", "confidence": 0.97, "type": "expense"},
    {"pattern": r"apple\s*pay|apple\.com|google\s*pay|google\s*payment|google\s*play", "category": "Abonnements/Digital", "subcategory": "Digital Services", "confidence": 0.95, "type": "expense"},
    {"pattern": r"amazon", "category": "Unbekannt", "subcategory": "Amazon-Rückfrage", "confidence": 0.70, "type": "expense"},  # Always prompts confirmation
    {"pattern": r"überweisung|dauerauftrag|sepa-überweisung", "category": "Transfer", "subcategory": "Überweisung", "confidence": 0.95, "type": "expense"}
]

# Budgets for Variable & Fixed categories (in Euros)
BUDGET_LIMITS = {
    "Wohnen": 1200.0,
    "Energie": 200.0,
    "Kommunikation": 50.0,
    "Medien / Streaming": 30.0,
    "Mobilität": 100.0,
    "Fitness": 40.0,
    "Versicherungen": 150.0,
    "Sonstige Fixkosten": 50.0,
    "Lebensmittel": 500.0,
    "Drogerie": 50.0,
    "Benzin": 150.0,
    "Auto": 100.0,
    "Kleidung": 100.0,
    "Gesundheit": 80.0,
    "Geschenke": 50.0,
    "Abonnements/Digital": 30.0,
    "Freizeit": 120.0,
    "Restaurant / Café": 150.0,
    "Transfer": 0.0,
    "Unbekannt": 0.0
}

import logging
import pandas as pd
from utils.sheets_handler import sheets_handler

logger = logging.getLogger(__name__)

DEFAULT_KEYWORDS = {
    "Lebensmittel": "lidl, aldi, rewe, kaufland, penny, netto, supermarkt",
    "Drogerie": "rossmann, dm, drogerie",
    "Benzin": "hem, shell, aral, tankstelle, esso, total, jet",
    "Medien / Streaming": "netflix, spotify, youtube, disney, apple music",
    "Abonnements/Digital": "apple, google, patreon, icloud",
    "Transfer": "überweisung, dauerauftrag, umbuchung",
    "Wohnen": "miete, wohnung, hausgeld",
    "Energie": "stadtwerke, strom, gas, wasser",
    "Kommunikation": "vodafone, telekom, o2, 1und1",
    "Mobilität": "bahn, bvg, vrr, fahrkarte, ticket",
    "Fitness": "mcfit, fitx, fitnessstudio, urban sports",
    "Versicherungen": "allianz, huk, devk, versicherung",
    "Restaurant / Café": "restaurant, café, bäckerei, pizzeria, burger, sushi",
    "Einkommen": "gehalt, lohn, salary, gehaltseingang",
    "Dividenden": "dividende",
    "Zinsen": "zinsen",
    "Cashback": "cashback",
    "Verkauf": "ebay, vinted, kleinanzeigen",
    "Investitionen (Sparpläne)": "etf, aktien, trade republic, scalable",
    "Altersvorsorge": "rente, riester, rürup, allianz"
}

def get_default_categories_flat() -> list[dict]:
    """Construct default rows for settings sheet."""
    rows = []
    for cat in CATEGORIES["expense"]["Fixkosten"] + CATEGORIES["expense"]["Variable Kosten"]:
        rows.append({"type": "expense", "name": cat, "keywords": DEFAULT_KEYWORDS.get(cat, ""), "active": "TRUE"})
    for cat in CATEGORIES["income"]["Einnahmen"]:
        rows.append({"type": "income", "name": cat, "keywords": DEFAULT_KEYWORDS.get(cat, ""), "active": "TRUE"})
    for cat in CATEGORIES["savings"]["Ersparnisse"]:
        rows.append({"type": "savings", "name": cat, "keywords": DEFAULT_KEYWORDS.get(cat, ""), "active": "TRUE"})
    return rows

def update_global_categories_dict(loaded_dict: dict):
    """Sync memory CATEGORIES dict with loaded categories from sheets."""
    exp_names = [item["name"] for item in loaded_dict.get("expense", [])]
    inc_names = [item["name"] for item in loaded_dict.get("income", [])]
    sav_names = [item["name"] for item in loaded_dict.get("savings", [])]
    
    if exp_names:
        CATEGORIES["expense"]["Variable Kosten"] = exp_names
    if inc_names:
        CATEGORIES["income"]["Einnahmen"] = inc_names
    if sav_names:
        CATEGORIES["savings"]["Ersparnisse"] = sav_names

def load_categories_from_sheets() -> dict:
    """Load all categories from the 'settings' tab in Google Sheets."""
    try:
        df = sheets_handler.read_settings_sheet()
        if df.empty or "name" not in df.columns or df["name"].dropna().empty:
            default_rows = get_default_categories_flat()
            df = pd.DataFrame(default_rows)
            sheets_handler.write_settings_sheet(df)
            
        result = {"expense": [], "income": [], "savings": []}
        for _, row in df.iterrows():
            t_val = str(row.get("type", "expense")).strip().lower()
            if t_val not in result:
                t_val = "expense"
            c_name = str(row.get("name", "")).strip()
            if not c_name:
                continue
            kw_raw = str(row.get("keywords", ""))
            if pd.isna(kw_raw) or kw_raw.lower() == "nan":
                kw_raw = ""
            keywords_list = [k.strip() for k in kw_raw.split(",") if k.strip()]
            act_raw = str(row.get("active", "TRUE")).strip().upper()
            is_active = act_raw in ["TRUE", "1", "YES", "WAHR"]
            
            result[t_val].append({
                "name": c_name,
                "keywords": keywords_list,
                "active": is_active
            })
            
        update_global_categories_dict(result)
        return result
    except Exception as e:
        logger.error(f"Error loading categories from sheets: {e}")
        fallback = {"expense": [], "income": [], "savings": []}
        for group, cats in CATEGORIES["expense"].items():
            for c in cats:
                fallback["expense"].append({"name": c, "keywords": [k.strip() for k in DEFAULT_KEYWORDS.get(c, "").split(",") if k.strip()], "active": True})
        for c in CATEGORIES["income"]["Einnahmen"]:
            fallback["income"].append({"name": c, "keywords": [k.strip() for k in DEFAULT_KEYWORDS.get(c, "").split(",") if k.strip()], "active": True})
        for c in CATEGORIES["savings"]["Ersparnisse"]:
            fallback["savings"].append({"name": c, "keywords": [k.strip() for k in DEFAULT_KEYWORDS.get(c, "").split(",") if k.strip()], "active": True})
        return fallback

def save_categories_to_sheets(categories_dict: dict) -> None:
    """Write all categories back to the 'settings' tab. Overwrites existing data."""
    rows = []
    for t_val in ["expense", "income", "savings"]:
        for item in categories_dict.get(t_val, []):
            kw_str = ", ".join(item.get("keywords", []))
            act_str = "TRUE" if item.get("active", True) else "FALSE"
            rows.append({
                "type": t_val,
                "name": item.get("name", "").strip(),
                "keywords": kw_str,
                "active": act_str
            })
    df = pd.DataFrame(rows)
    sheets_handler.write_settings_sheet(df)
    update_global_categories_dict(categories_dict)

def add_category(type_: str, name: str, keywords: list[str]) -> None:
    """Add a new category. type_ must be 'expense', 'income', or 'savings'."""
    cats = load_categories_from_sheets()
    t_clean = type_.lower().strip()
    if t_clean not in cats:
        t_clean = "expense"
        
    existing = next((c for c in cats[t_clean] if c["name"].lower() == name.lower().strip()), None)
    if not existing:
        cats[t_clean].append({"name": name.strip(), "keywords": keywords, "active": True})
    else:
        existing["keywords"] = list(set(existing["keywords"] + keywords))
        existing["active"] = True
        
    save_categories_to_sheets(cats)

def delete_category(type_: str, name: str) -> None:
    """Delete a category by name and type."""
    cats = load_categories_from_sheets()
    t_clean = type_.lower().strip()
    if t_clean in cats:
        cats[t_clean] = [c for c in cats[t_clean] if c["name"].lower() != name.lower().strip()]
        save_categories_to_sheets(cats)

def update_category_keywords(type_: str, name: str, keywords: list[str]) -> None:
    """Update keywords for a given category."""
    cats = load_categories_from_sheets()
    t_clean = type_.lower().strip()
    if t_clean in cats:
        for item in cats[t_clean]:
            if item["name"].lower() == name.lower().strip():
                item["keywords"] = keywords
                break
        save_categories_to_sheets(cats)

def count_transactions_with_category(category_name: str) -> int:
    """Count how many transactions across all sheet tabs use category_name."""
    try:
        sheet_names = sheets_handler.get_all_sheet_names()
        count = 0
        cat_target = category_name.strip().lower()
        for s_name in sheet_names:
            s_lower = s_name.lower()
            if "expenses" in s_lower or "income" in s_lower or "savings" in s_lower or "." in s_lower:
                df = sheets_handler.read_sheet_data(s_name)
                if df is not None and not df.empty:
                    df.columns = [str(c).strip().lower() for c in df.columns]
                    col_cat = next((c for c in df.columns if c in ["kategorie", "category"]), None)
                    if col_cat:
                        matches = df[df[col_cat].astype(str).str.strip().str.lower() == cat_target]
                        count += len(matches)
        return count
    except Exception as e:
        logger.error(f"Error counting transactions for category {category_name}: {e}")
        return 0
