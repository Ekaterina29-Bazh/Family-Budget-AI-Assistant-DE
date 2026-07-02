# skills/text_parser.py

import datetime
import logging
from utils.gemini_client import gemini_client

logger = logging.getLogger(__name__)

def parse_text(message: str) -> dict:
    """
    Skill 1: Parses German text to extract a structured transaction.
    Returns a dictionary matching the target JSON schema.
    """
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    prompt = f"""
Du bist FamilyBudget AI. Analysiere den folgenden deutschen Text.
Bestimme zuerst, ob es sich um eine finanzielle Transaktion handelt (z.B. Einnahme, Ausgabe, Ersparnis, Buchung, wie "Lidl 23,50 €" oder "Gehalt überwiesen").
Falls es sich um eine allgemeine Frage, Begrüßung (z.B. "Hallo", "Guten Morgen"), ein unbezogenes Gespräch, reines Löschen/Abbrechen oder eine reine Analyseanfrage handelt, setze "is_transaction" auf false.

Regeln für die Felder:
1. "is_transaction": true, wenn der Text eine finanzielle Transaktion beschreibt (Ausgabe, Einnahme oder Ersparnis). Andernfalls false.
2. "date": Das Datum im Format "YYYY-MM-DD". Heutiges Datum (Standardwert für 'date', falls im Text kein anderes Datum/Monat angegeben ist): {today_str}
3. "date_specified": true, falls im Text ein konkretes Datum, ein Monat (z. B. "im Mai", "Juni") oder ein relativer Tag (z. B. "heute", "gestern", "letzte Woche") explizit oder implizit genannt wurde. Andernfalls false.
4. "merchant": Der Name des Händlers, der Quelle oder des Empfängers (z. B. "Lidl", "HEM Tankstelle", "eBay").
5. "merchant_specified": true, falls ein Händler, Empfänger oder eine Quelle im Text genannt wurde. Andernfalls false.
6. "amount": Der Geldbetrag als Fließkommazahl (Float, z.B. 23.50). Verwende einen Punkt als Dezimaltrennzeichen.
7. "amount_specified": true, falls ein Geldbetrag im Text genannt wurde. Andernfalls false.
8. "type": Eines der folgenden: "expense" (Standard für Ausgaben/Käufe), "income" (für Einnahmen wie Gehalt, Verkauf), "savings" (für Sparraten, Altersvorsorge, ETF).
9. "person": "katja", "dirk" oder "shared". Falls im Text nicht explizit Katja oder Dirk genannt wird, verwende immer "shared".
10. "category_hint": Eine im Text erwähnte oder angedeutete Kategorie (z. B. "Lebensmittel", "Benzin", "Gehalt"). Dies ist nur ein Hinweis für die Klassifizierung.
11. "source": Immer "text".
12. "note": Eine optionale kurze Notiz oder Zusatzinfo aus dem Text (z.B. "für Kindergeburtstag"). Falls keine vorhanden, leerer String "".

Antworte ausschließlich mit einem validen JSON-Objekt ohne zusätzlichen Text. Das JSON muss exakt diese Struktur haben:
{{
  "is_transaction": true | false,
  "date": "YYYY-MM-DD",
  "date_specified": true | false,
  "merchant": "Händlername oder Quelle",
  "merchant_specified": true | false,
  "amount": 0.00,
  "amount_specified": true | false,
  "type": "expense | income | savings",
  "person": "katja | dirk | shared",
  "category_hint": "Hinweis",
  "source": "text",
  "note": "optional"
}}

Text zum Analysieren:
"{message}"
"""

    try:
        parsed = gemini_client.generate_json(prompt)
        # Ensure default values and types
        if not parsed.get("date"):
            parsed["date"] = today_str
        if parsed.get("amount"):
            try:
                parsed["amount"] = float(str(parsed["amount"]).replace(",", "."))
            except ValueError:
                parsed["amount"] = 0.0
        else:
            parsed["amount"] = 0.0
            
        # Standardize types and person
        parsed["type"] = parsed.get("type", "expense").lower()
        p = str(parsed.get("person", "shared")).lower()
        if "katja" in p:
            parsed["person"] = "katja"
        elif "dirk" in p:
            parsed["person"] = "dirk"
        else:
            parsed["person"] = "shared"
                
        parsed["merchant"] = parsed.get("merchant", "Unbekannt")
        parsed["source"] = "text"
        parsed["note"] = parsed.get("note", "")
        
        # Ensure specified flags exist
        parsed["is_transaction"] = bool(parsed.get("is_transaction", True))
        parsed["date_specified"] = bool(parsed.get("date_specified", False))
        parsed["merchant_specified"] = bool(parsed.get("merchant_specified", False))
        parsed["amount_specified"] = bool(parsed.get("amount_specified", False))
        
        return parsed
    except Exception as e:
        logger.error(f"Error in parse_text: {e}")
        # Fallback empty structure
        return {
            "is_transaction": False,
            "date": today_str,
            "date_specified": False,
            "person": "shared",
            "merchant": "Unbekannt",
            "merchant_specified": False,
            "amount": 0.0,
            "amount_specified": False,
            "type": "expense",
            "category_hint": "",
            "source": "text",
            "note": f"Error parsing: {str(e)}"
        }

def clarify_pending_transaction(pending_tx: dict, user_reply: str) -> dict:
    """
    Skill 1b: Clarifies an incomplete transaction by merging it with the user's clarification response.
    """
    prompt = f"""
Du bist FamilyBudget AI. Wir haben eine unvollständige oder unklare Transaktion:
{pending_tx}

Der Benutzer hat auf unsere Nachfrage zur Klärung folgende Antwort gegeben:
"{user_reply}"

Aktualisiere die Transaktionsdetails basierend auf der Antwort des Benutzers.
Wenn der Benutzer ein Datum oder einen Monat nennt (z.B. "Mai", "im Juni", "letzter Monat"), passe das Feld "date" an und setze "date_specified" auf true.
Wenn der Benutzer einen Händler nennt, passe "merchant" an und setze "merchant_specified" auf true.
Wenn der Benutzer einen Betrag nennt, passe "amount" an und setze "amount_specified" auf true.
Wenn der Benutzer eine Kategorie nennt oder auswählt, passe "category" an.
Wenn der Benutzer sagt "passt so", "heute" oder den Standardwert bestätigt, setze das entsprechende specified-Feld auf true (z.B. "date_specified" auf true für heute/passt so).

Antworte ausschließlich mit einem validen JSON-Objekt ohne zusätzlichen Text. Das JSON muss exakt dieselbe Struktur wie die Transaktion haben, mit aktualisierten Werten:
{{
  "is_transaction": true,
  "date": "YYYY-MM-DD",
  "date_specified": true | false,
  "merchant": "Händlername oder Quelle",
  "merchant_specified": true | false,
  "amount": 0.00,
  "amount_specified": true | false,
  "type": "expense | income | savings",
  "person": "katja | dirk | shared | unknown",
  "category": "...",
  "subcategory": "...",
  "confidence": 0.00 to 1.00,
  "source": "text",
  "note": "..."
}}
"""
    try:
        parsed = gemini_client.generate_json(prompt)
        # Ensure default values and types
        if parsed.get("amount"):
            try:
                parsed["amount"] = float(str(parsed["amount"]).replace(",", "."))
            except ValueError:
                parsed["amount"] = pending_tx.get("amount", 0.0)
        else:
            parsed["amount"] = pending_tx.get("amount", 0.0)
            
        parsed["type"] = parsed.get("type", pending_tx.get("type", "expense")).lower()
        parsed["person"] = parsed.get("person", pending_tx.get("person", "shared")).lower()
        parsed["merchant"] = parsed.get("merchant", pending_tx.get("merchant", "Unbekannt"))
        parsed["source"] = "text"
        parsed["note"] = parsed.get("note", pending_tx.get("note", ""))
        
        # Ensure specified flags are updated
        parsed["is_transaction"] = True
        parsed["date_specified"] = bool(parsed.get("date_specified", pending_tx.get("date_specified", False)))
        parsed["merchant_specified"] = bool(parsed.get("merchant_specified", pending_tx.get("merchant_specified", False)))
        parsed["amount_specified"] = bool(parsed.get("amount_specified", pending_tx.get("amount_specified", False)))
        
        return parsed
    except Exception as e:
        logger.error(f"Error clarifying pending transaction: {e}")
        return pending_tx

def generate_general_response(message: str) -> str:
    """
    Generates a general assistant response for non-transaction questions or conversation.
    """
    prompt = f"""
Du bist FamilyBudget AI, ein intelligenter und freundlicher Finanzassistent für eine Familie (Katja und Dirk).
Der Benutzer hat folgende Nachricht gesendet (keine direkte Buchungstransaktion):
"{message}"

Antworte freundlich, kurz und präzise auf Deutsch. Du kannst erklären, wie du helfen kannst (z.B. Ausgaben eintragen, PDF-Kontoauszüge einlesen, Auswertungen erstellen). Halte dich kurz.
"""
    try:
        response = gemini_client.generate(prompt)
        return response
    except Exception as e:
        return f"Hallo! Ich bin dein FamilyBudget AI Assistant. Wie kann ich dir helfen? (Fehler bei der Antwortgenerierung: {e})"

