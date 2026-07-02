# skills/pdf_parsing_skill.py

import io
import pdfplumber
import logging
from utils.gemini_client import gemini_client

logger = logging.getLogger(__name__)

def parse_pdf(file_bytes: bytes, context: str = "") -> list[dict]:
    """
    Skill 2: Extract text from bank PDF using pdfplumber,
    and structure transactions using Gemini (including classification).
    
    Uses a SINGLE Gemini call that both extracts AND classifies transactions,
    avoiding the N+1 API call problem on the free tier.
    """
    from utils.categories import CATEGORIES, STATIC_RULES
    import re
    
    # 1. Extract raw text from PDF bytes
    raw_text = ""
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    raw_text += f"\n--- PAGE {page_idx + 1} ---\n{text}"
    except Exception as e:
        logger.error(f"Error reading PDF with pdfplumber: {e}")
        raise ValueError(f"Fehler beim Lesen der PDF-Datei: {str(e)}")

    if not raw_text.strip():
        raise ValueError("Es konnte kein Text aus der PDF extrahiert werden. Ist die PDF gescannt oder leer?")

    # Build a flat category list for the prompt so Gemini classifies in one shot
    all_categories = {}
    for tx_type, groups in CATEGORIES.items():
        for group_name, cats in groups.items():
            for cat in cats:
                all_categories[cat] = tx_type

    category_list_str = "\n".join(f"  - {cat} (Typ: {tx_type})" for cat, tx_type in all_categories.items())

    context_hint = ""
    if context and context.strip():
        context_hint = f"""\nZUSÄTZLICHER HINWEIS DES BENUTZERS (WICHTIG — berücksichtige diesen Hinweis unbedingt bei der Extraktion, Datumskorrektur, Namenszuordnung und Kategorisierung):\nBENUTZER-KOMMENTAR: {context.strip()}\n"""

    # 2. Single Gemini call: extract AND classify
    prompt = f"""
Du bist FamilyBudget AI. Analysiere den folgenden Kontoauszug-Text und extrahiere alle Buchungen (Transaktionen, Einnahmen, Ersparnisse).

{context_hint}
Regeln für die Extraktion:
- Suche nach allen Geldbewegungen (Abbuchungen, Überweisungen, Gutschriften).
- Bestimme das Datum der Transaktion im Format "YYYY-MM-DD".
- Bestimme den Händlernamen oder den Verwendungszweck/Empfänger/Sender ("merchant").
- Bestimme den Geldbetrag ("amount") als positive Fließkommazahl (float).
- Bestimme den "type" der Transaktion:
  - "expense": bei allen regulären Ausgaben, Lastschriften, Kartenzahlungen, Geldabgängen.
  - "income": bei Gehaltseingängen, Gutschriften, Geldeingängen.
  - "savings": bei erkennbaren Sparraten, Überweisungen an Sparkonten oder Depots.
- Bestimme die "person" (katja, dirk, shared, unknown):
  - Bei regulären Ausgaben ("type" ist "expense"): immer "shared".
  - Bei Einnahmen oder Ersparnissen: Falls aus dem Text erkennbar ist, ob es Katja oder Dirk betrifft, ordne es zu. Andernfalls "unknown".

Regeln für die Kategorisierung (WICHTIG — wähle die passendste Kategorie aus dieser Liste):
{category_list_str}
- Wenn du unsicher bist, wähle "Unbekannt" mit confidence unter 0.50.
- Setze die "confidence" auf 0.0 bis 1.0 basierend auf deiner Sicherheit.

- Bestimme eine optionale kurze Notiz ("note").

Antworte ausschließlich mit einem validen JSON-Array von Objekten. Verwende keine Markdown-Formatierung außer dem reinen JSON-Array.
Das Format muss exakt so aussehen:
[
  {{
    "date": "YYYY-MM-DD",
    "merchant": "Händlername / Zweck",
    "amount": 12.34,
    "type": "expense | income | savings",
    "person": "katja | dirk | shared | unknown",
    "category": "Kategoriename aus der Liste oben",
    "confidence": 0.85,
    "note": "optional"
  }},
  ...
]

Hier ist der Kontoauszug-Text:
\"\"\"{raw_text}\"\"\"
"""
    try:
        extracted_txs = gemini_client.generate_json(prompt)
        if not isinstance(extracted_txs, list):
            if isinstance(extracted_txs, dict) and "transactions" in extracted_txs:
                extracted_txs = extracted_txs["transactions"]
            elif isinstance(extracted_txs, dict):
                extracted_txs = [extracted_txs]
            else:
                extracted_txs = []
    except Exception as e:
        logger.error(f"Error parsing PDF transactions with Gemini: {e}")
        raise ValueError(f"Gemini konnte die Buchungen aus der PDF nicht parsen: {str(e)}")

    # 3. Post-process: apply static rules as overrides (no extra API calls)
    valid_categories = set(all_categories.keys())
    classified_txs = []
    for tx in extracted_txs:
        try:
            merchant = tx.get("merchant", "Unbekannt")
            amount = float(tx.get("amount", 0.0))
            tx_type = tx.get("type", "expense").lower()
            category = tx.get("category", "Unbekannt")
            confidence = float(tx.get("confidence", 0.70))

            # Override with static rules if they match (higher confidence)
            merchant_clean = merchant.strip().lower()
            for rule in STATIC_RULES:
                if re.search(rule["pattern"], merchant_clean):
                    category = rule["category"]
                    confidence = rule["confidence"]
                    break

            # Validate category
            if category not in valid_categories:
                category = "Unbekannt"
                confidence = min(confidence, 0.40)

            full_tx = {
                "date": tx.get("date"),
                "type": tx_type,
                "person": tx.get("person", "shared"),
                "merchant": merchant,
                "amount": amount,
                "category": category,
                "subcategory": "-",
                "source": "pdf",
                "confidence": confidence,
                "note": tx.get("note", "")
            }
            classified_txs.append(full_tx)
        except Exception as e:
            logger.error(f"Error processing PDF transaction {tx}: {e}")
            
    return classified_txs

def parse_image(file_bytes: bytes, mime_type: str, context: str = "") -> list[dict]:
    """
    Skill 2b: Extract and classify transactions from receipts/screenshots.
    Uses a SINGLE Gemini call (extract + classify) to stay within free-tier quota.
    """
    from google.genai import types
    from utils.categories import CATEGORIES, STATIC_RULES
    import re

    # Build flat category list for the prompt
    all_categories = {}
    for tx_type, groups in CATEGORIES.items():
        for group_name, cats in groups.items():
            for cat in cats:
                all_categories[cat] = tx_type

    category_list_str = "\n".join(f"  - {cat} (Typ: {tx_type})" for cat, tx_type in all_categories.items())

    context_hint = ""
    if context and context.strip():
        context_hint = f"""\nZUSÄTZLICHER HINWEIS DES BENUTZERS (WICHTIG — berücksichtige diesen Hinweis unbedingt bei der Extraktion, Datumskorrektur, Namenszuordnung und Kategorisierung):\nBENUTZER-KOMMENTAR: {context.strip()}\n"""

    prompt = f"""
Du bist FamilyBudget AI. Analysiere das hochgeladene Bild eines Finanzdokuments (z. B. Screenshot, Quittung, Abrechnung, Einnahmen/Ersparnisse-Nachweis) und extrahiere alle Buchungen (Ausgaben, Einnahmen, Ersparnisse).

{context_hint}
Regeln für die Extraktion:
- Suche nach allen Geldbewegungen (Beträgen, Überweisungen, Gehalt, Sparguthaben, Dividenden, Zinsen).
- Bestimme das Datum im Format "YYYY-MM-DD" (falls kein Jahr oder Datum erkennbar ist, verwende das heutige Jahr/Datum).
- Bestimme den Händlernamen, die Quelle oder den Empfänger/Sender ("merchant").
- Bestimme den Geldbetrag ("amount") als positive Fließkommazahl (float).
- Bestimme den "type" der Transaktion:
  - "expense": bei allen regulären Ausgaben, Lastschriften, Kartenzahlungen.
  - "income": bei Gehaltseingängen, Gutschriften, Geldeingängen, Dividenden, Zinsen, Cashback.
  - "savings": bei erkennbaren Sparraten, Überweisungen an Sparkonten, Depots, ETFs, Altersvorsorge.
- Bestimme die "person" (katja, dirk, shared, unknown):
  - Bei regulären Ausgaben ("type" ist "expense"): immer "shared".
  - Bei Einnahmen ("income") oder Ersparnissen ("savings"): Versuche herauszufinden, ob es Katja oder Dirk betrifft. Falls nicht erkennbar, setze "unknown".

Regeln für die Kategorisierung (WICHTIG — wähle die passendste Kategorie aus dieser Liste):
{category_list_str}
- Wenn du unsicher bist, wähle "Unbekannt" mit confidence unter 0.50.
- Setze die "confidence" auf 0.0 bis 1.0 basierend auf deiner Sicherheit.

- Bestimme eine optionale kurze Notiz ("note").

Antworte ausschließlich mit einem validen JSON-Array von Objekten.
Das Format muss exakt so aussehen:
[
  {{
    "date": "YYYY-MM-DD",
    "merchant": "Händlername / Quelle",
    "amount": 12.34,
    "type": "expense | income | savings",
    "person": "katja | dirk | shared | unknown",
    "category": "Kategoriename aus der Liste oben",
    "confidence": 0.85,
    "note": "optional"
  }},
  ...
]
"""
    
    contents = [
        types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
        prompt
    ]
    
    try:
        extracted_txs = gemini_client.generate_json(contents)
        if not isinstance(extracted_txs, list):
            if isinstance(extracted_txs, dict) and "transactions" in extracted_txs:
                extracted_txs = extracted_txs["transactions"]
            elif isinstance(extracted_txs, dict):
                extracted_txs = [extracted_txs]
            else:
                extracted_txs = []
    except Exception as e:
        logger.error(f"Error parsing image transactions with Gemini: {e}")
        raise ValueError(f"Gemini konnte das Bild nicht parsen: {str(e)}")
        
    # Post-process: apply static rules as overrides (no extra API calls)
    valid_categories = set(all_categories.keys())
    classified_txs = []
    for tx in extracted_txs:
        try:
            merchant = tx.get("merchant", "Unbekannt")
            amount = float(tx.get("amount", 0.0))
            tx_type = tx.get("type", "expense").lower()
            category = tx.get("category", "Unbekannt")
            confidence = float(tx.get("confidence", 0.70))

            # Override with static rules if they match
            merchant_clean = merchant.strip().lower()
            for rule in STATIC_RULES:
                if re.search(rule["pattern"], merchant_clean):
                    category = rule["category"]
                    confidence = rule["confidence"]
                    break

            if category not in valid_categories:
                category = "Unbekannt"
                confidence = min(confidence, 0.40)

            full_tx = {
                "date": tx.get("date"),
                "type": tx_type,
                "person": tx.get("person", "shared"),
                "merchant": merchant,
                "amount": amount,
                "category": category,
                "subcategory": "-",
                "source": "image",
                "confidence": confidence,
                "note": tx.get("note", "")
            }
            classified_txs.append(full_tx)
        except Exception as e:
            logger.error(f"Error processing image transaction {tx}: {e}")
            
    return classified_txs
