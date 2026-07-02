import re
from utils.categories import CATEGORIES, STATIC_RULES, load_categories_from_sheets

def classify_transaction(merchant: str, amount: float, category_hint: str = None, tx_type: str = "expense") -> dict:
    """
    Skill 3: Determines the category and subcategory of a transaction,
    and returns a confidence score (0.0 - 1.0).
    """
    amount = float(amount)
    merchant_clean = merchant.strip().lower()
    
    # 1. Check static rules first
    for rule in STATIC_RULES:
        if re.search(rule["pattern"], merchant_clean):
            if "amazon" in merchant_clean:
                return {
                    "category": "Unbekannt",
                    "subcategory": "Amazon-Rückfrage",
                    "confidence": 0.70
                }
            return {
                "category": rule["category"],
                "subcategory": rule["subcategory"],
                "confidence": rule["confidence"]
            }

    # 1b. Check keywords from user-defined categories in Sheets
    try:
        active_cats = load_categories_from_sheets()
        for t_val, items in active_cats.items():
            for item in items:
                if item.get("active", True):
                    cat_name = item.get("name")
                    for kw in item.get("keywords", []):
                        if kw and len(kw) >= 2 and kw.lower() in merchant_clean:
                            return {
                                "category": cat_name,
                                "subcategory": "-",
                                "confidence": 0.98
                            }
    except Exception:
        pass

    # 2. Check category_hint
    if category_hint:
        hint_clean = category_hint.strip().lower()
        for cat_group, cats in CATEGORIES["expense"].items():
            for c in cats:
                if c.lower() in hint_clean:
                    return {"category": c, "subcategory": "-", "confidence": 0.95}
        for c in CATEGORIES["income"]["Einnahmen"]:
            if c.lower() in hint_clean:
                return {"category": c, "subcategory": "-", "confidence": 0.95}
        for c in CATEGORIES["savings"]["Ersparnisse"]:
            if c.lower() in hint_clean:
                return {"category": c, "subcategory": "-", "confidence": 0.95}

    # 3. Fallback: Use Gemini to classify based on categories list
    from utils.gemini_client import gemini_client
    
    # Flatten categories for prompt
    categories_schema = {
        "expense": CATEGORIES["expense"],
        "income": CATEGORIES["income"],
        "savings": CATEGORIES["savings"]
    }
    
    prompt = f"""
Klassifiziere die folgende finanzielle Transaktion basierend auf unserem Kategorien-System.

Händler/Quelle: "{merchant}"
Betrag: {amount} EUR
Typ: {tx_type}
Kategorie-Hinweis (optional): "{category_hint or ''}"

Verfügbares Kategorien-System:
{categories_schema}

Deine Aufgaben:
1. Bestimme die passende Hauptkategorie und Unterkategorie.
2. Berechne einen Confidence-Score (0.0 bis 1.0) dafür, wie sicher die Zuordnung ist.
   - Wenn der Händler völlig unbekannt ist und auch kein Kategorie-Hinweis hilft, wähle Hauptkategorie "Unbekannt" und einen Confidence-Score unter 0.50 (z.B. 0.30).
   - Wenn du dir sehr sicher bist, gib einen hohen Score (z.B. 0.85 bis 0.95).

Antworte exakt in dieser JSON-Struktur:
{{
  "category": "Hauptkategorie",
  "subcategory": "Unterkategorie oder -",
  "confidence": 0.85
}}
"""
    try:
        response = gemini_client.generate_json(prompt)
        cat = response.get("category", "Unbekannt")
        sub = response.get("subcategory", "-")
        conf = float(response.get("confidence", 0.40))
        
        # Ensure category is valid in our system
        all_valid_cats = []
        for group in CATEGORIES.values():
            for cats in group.values():
                all_valid_cats.extend(cats)
                
        if cat not in all_valid_cats:
            cat = "Unbekannt"
            conf = 0.30
            
        return {
            "category": cat,
            "subcategory": sub,
            "confidence": conf
        }
    except Exception:
        # Emergency fallback
        return {
            "category": "Unbekannt",
            "subcategory": "-",
            "confidence": 0.30
        }
