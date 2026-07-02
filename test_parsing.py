# test_parsing.py

import json
from skills.text_parser import parse_text
from skills.classifier import classify_transaction

inputs = [
    "Heute bei Lidl 23,50 € für Lebensmittel ausgegeben",
    "Gestern bei Rossmann 12,50 ausgegeben",
    "Hab gerade 40 Euro für Max bezahlt",
    "Katja hat heute ihr Gehalt bekommen, 2800 Euro",
    "Dirk hat diesen Monat 200 Euro in die Altersvorsorge eingezahlt"
]

for txt in inputs:
    print(f"\nInput: '{txt}'")
    parsed = parse_text(txt)
    print("Parsed JSON:")
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
    
    # Classify
    classification = classify_transaction(
        parsed.get("merchant"),
        parsed.get("amount"),
        category_hint=parsed.get("category_hint"),
        tx_type=parsed.get("type")
    )
    print("Classification:")
    print(json.dumps(classification, indent=2, ensure_ascii=False))
