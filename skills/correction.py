# skills/correction.py

import logging
from datetime import datetime
from utils.sheets_handler import sheets_handler
from utils.gemini_client import gemini_client
from utils.categories import CATEGORIES

logger = logging.getLogger(__name__)

def parse_correction_request(message: str) -> dict:
    """
    Uses Gemini to extract target parameters for correction from user text.
    """
    today_str = datetime.today().strftime("%Y-%m-%d")
    
    # Extract all valid categories for the prompt
    all_cats = []
    for grp in CATEGORIES.values():
        for subgrp in grp.values():
            all_cats.extend(subgrp)
            
    prompt = f"""
Du bist FamilyBudget AI. Der Benutzer möchte eine fehlerhafte Kategorisierung korrigieren.
Analysiere die Korrekturanfrage und extrahiere:
1. "date": Das Datum der ursprünglichen Buchung im Format "YYYY-MM-DD" (falls genannt, sonst null).
2. "merchant": Den Namen des Händlers der betroffenen Buchung (z.B. "HEM Tankstelle" oder "Amazon").
3. "amount": Den Betrag der Buchung als Fließkommazahl (float, z.B. 68.51) oder null, falls nicht erwähnt.
4. "new_category": Die neue Kategorie, der die Buchung zugeordnet werden soll (muss eine der folgenden sein: {all_cats}).

Antworte ausschließlich mit einem validen JSON-Objekt.
Das JSON-Format:
{{
  "date": "YYYY-MM-DD" oder null,
  "merchant": "Händlername",
  "amount": 12.34 oder null,
  "new_category": "Neue Kategorie"
}}

Text:
"{message}"
"""
    try:
        res = gemini_client.generate_json(prompt)
        # Ensure values
        if res.get("amount"):
            res["amount"] = float(str(res["amount"]).replace(",", "."))
        return res
    except Exception as e:
        logger.error(f"Error parsing correction request: {e}")
        return {"date": None, "merchant": None, "amount": None, "new_category": None}

def correct_transaction(message: str) -> dict:
    """
    Skill 6: Corrects an existing transaction.
    Returns a dictionary indicating the result:
    {
      "status": "success | error | disambiguate",
      "message": "User text response",
      "matches": [...] # List of matching rows if disambiguate
    }
    """
    # 1. Parse correction parameters
    params = parse_correction_request(message)
    target_merchant = params.get("merchant")
    new_category = params.get("new_category")
    target_date = params.get("date")
    target_amount = params.get("amount")

    if not target_merchant or not new_category:
        return {
            "status": "error",
            "message": "❌ Ich konnte den Händlernamen oder die neue Kategorie aus deiner Nachricht nicht erkennen. Bitte versuche es so: 'Korrigiere die HEM-Buchung vom 22.06., das war Auto statt Benzin.'"
        }

    # Verify if category is valid
    all_valid_cats = []
    for grp in CATEGORIES.values():
        for subgrp in grp.values():
            all_valid_cats.extend(subgrp)
    if new_category not in all_valid_cats:
        return {
            "status": "error",
            "message": f"❌ Die Kategorie '{new_category}' ist in unserem System nicht bekannt."
        }

    # 2. Get transaction worksheet
    # Use specified date to determine sheet, or fall back to current month
    if target_date:
        month_str = target_date[:7]
    else:
        month_str = datetime.today().strftime("%Y-%m")

    df = sheets_handler.get_transactions(month_str)
    if df.empty:
        return {
            "status": "error",
            "message": f"❌ Ich konnte für den Monat {month_str} keine Buchungen im Tab finden."
        }

    # 3. Find matching rows
    # Clean df columns
    df["Betrag_float"] = df["Betrag"].astype(str).str.replace(",", ".").astype(float)
    df["Händler_lower"] = df["Händler"].astype(str).str.lower().str.strip()
    
    matches = df.copy()
    
    # Filter by Date
    if target_date:
        matches = matches[matches["Datum"] == target_date]
        
    # Filter by Merchant
    matches = matches[matches["Händler_lower"].str.contains(target_merchant.lower(), na=False)]
    
    # Filter by Amount
    if target_amount:
        matches = matches[(matches["Betrag_float"] - target_amount).abs() < 0.01]

    if matches.empty:
        # If no matches found with exact date, try searching the entire sheet for this merchant
        matches = df[df["Händler_lower"].str.contains(target_merchant.lower(), na=False)]
        if target_amount:
            matches = matches[(matches["Betrag_float"] - target_amount).abs() < 0.01]
            
        if matches.empty:
            return {
                "status": "error",
                "message": f"❌ Keine passende Buchung für '{target_merchant}' im Monat {month_str} gefunden."
            }

    # 4. Handle results
    if len(matches) == 1:
        # Exactly one match: perform update
        matched_row = matches.iloc[0]
        actual_date = matched_row["Datum"]
        actual_merchant = matched_row["Händler"]
        actual_amount = float(str(matched_row["Betrag"]).replace(",", "."))
        old_category = matched_row["Kategorie"]
        
        success = sheets_handler.update_transaction(actual_date, actual_merchant, actual_amount, new_category)
        if success:
            return {
                "status": "success",
                "message": f"✅ Korrigiert:\n" \
                           f"**{actual_merchant}** | {actual_date} | {actual_amount:,.2f} € → Kategorie geändert: **{old_category}** zu **{new_category}**",
                "updated_transaction": {
                    "date": actual_date,
                    "merchant": actual_merchant,
                    "amount": actual_amount,
                    "category": new_category
                }
            }
        else:
            return {
                "status": "error",
                "message": "❌ Fehler beim Aktualisieren des Sheets."
            }
            
    else:
        # Multiple matches found: need disambiguation
        match_list = []
        for idx, row in matches.iterrows():
            match_list.append({
                "index": idx,
                "date": row["Datum"],
                "merchant": row["Händler"],
                "amount": float(str(row["Betrag"]).replace(",", ".")),
                "category": row["Kategorie"]
            })
            
        prompt_text = f"Es gibt mehrere passenden Buchungen für '{target_merchant}' am {target_date or month_str}:\n"
        for i, m in enumerate(match_list):
            prompt_text += f"[{chr(65 + i)}] {m['merchant']} – {m['amount']:,.2f} € vom {m['date']} (Aktuelle Kategorie: {m['category']})\n"
        prompt_text += "Welche soll ich ändern?"
        
        return {
            "status": "disambiguate",
            "message": prompt_text,
            "matches": match_list,
            "new_category": new_category
        }
