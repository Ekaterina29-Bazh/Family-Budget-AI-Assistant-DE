import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv(override=True)

def inspect_tabs():
    creds_path = "service_account.json"
    raw_id = os.environ.get("SPREADSHEET_ID") or os.environ.get("SPREDSHEET_ID")
    
    import re
    spreadsheet_id = raw_id
    if "docs.google.com/spreadsheets" in raw_id:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", raw_id)
        if match:
            spreadsheet_id = match.group(1)
            
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
    service = build("sheets", "v4", credentials=creds)
    
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_names = [s["properties"]["title"] for s in spreadsheet.get("sheets", [])]
    
    print("Sheets in spreadsheet:", sheet_names)
    
    for name in sheet_names:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{name}'!A1:I5"
        ).execute()
        rows = result.get("values", [])
        print(f"\nTab: '{name}'")
        print(f"Number of rows returned (capped at 5): {len(rows)}")
        if rows:
            print("Row 1 (Headers):", rows[0])
            for i, r in enumerate(rows[1:]):
                print(f"Row {i+2}:", r)

if __name__ == '__main__':
    inspect_tabs()
