# skills/sheets_writer.py

from utils.sheets_handler import sheets_handler

def write_to_sheets(transaction: dict) -> str:
    """
    Skill 4: Writes a classified transaction to the Google Sheet or local Excel fallback.
    Returns a success confirmation message in German.
    """
    success = sheets_handler.add_transaction(transaction)
    
    if success:
        # Get active month sheets data to calculate budget consumption
        date_val = transaction.get("date")
        month_str = date_val[:7] if date_val else ""
        merchant = transaction.get("merchant", "")
        amount = transaction.get("amount", 0.0)
        category = transaction.get("category", "")
        
        storage_info = "Google Sheets" if sheets_handler.use_google else "lokale Excel-Datei"
        message = f"✅ Ich habe die Transaktion per Chat in **{storage_info}** aufgenommen:\n" \
                  f"Datum: {date_val} | Händler: {merchant} | Betrag: {amount:,.2f} € | Kategorie: {category}"
        
        # Show category total spending so far this month
        if transaction.get("type") == "expense" and category and category != "Unbekannt":
            tx_df = sheets_handler.get_transactions(month_str)
            if not tx_df.empty:
                expenses_df = tx_df[
                    (tx_df["Kategorie"] == category) & 
                    (tx_df["Typ"].str.lower() == "expense")
                ]
                total_spent = expenses_df["Betrag"].astype(float).sum()
                message += f"\n\n📊 Gesamtausgaben in der Kategorie **{category}** diesen Monat: {total_spent:,.2f} €"
        return message
    else:
        return "❌ Die Transaktion konnte nicht in das Sheet eingetragen werden."
