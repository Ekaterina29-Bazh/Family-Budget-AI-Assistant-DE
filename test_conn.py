import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv(override=True)

def test_connection():
    creds_path = "service_account.json"
    raw_id = os.environ.get("SPREADSHEET_ID") or os.environ.get("SPREDSHEET_ID")
    
    print("Raw ID from env:", raw_id)
    
    import re
    spreadsheet_id = raw_id
    if "docs.google.com/spreadsheets" in raw_id:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", raw_id)
        if match:
            spreadsheet_id = match.group(1)
            
    print("Extracted Spreadsheet ID:", spreadsheet_id)
    
    if not os.path.exists(creds_path):
        print("Error: service_account.json not found!")
        return
        
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
        service = build("sheets", "v4", credentials=creds)
        
        print("Attempting to get spreadsheet metadata...")
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        print("Success! Title:", spreadsheet.get("properties", {}).get("title"))
        print("Sheets in spreadsheet:", [s["properties"]["title"] for s in spreadsheet.get("sheets", [])])
    except Exception as e:
        print("Connection failed with exception:")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_connection()
