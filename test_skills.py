# test_skills.py

import os
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

# Import utility classes and skills
from utils.categories import CATEGORIES, BUDGET_LIMITS
from utils.sheets_handler import sheets_handler, LOCAL_FILE
from skills.text_parser import parse_text, clarify_pending_transaction, generate_general_response
from skills.classifier import classify_transaction
from skills.sheets_writer import write_to_sheets
from skills.analytics import generate_analytics
from skills.correction import correct_transaction, parse_correction_request
from skills.pdf_parsing_skill import parse_pdf

class TestFamilyBudgetSkills(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Ensure we use local excel fallback for tests and start fresh
        if os.path.exists(LOCAL_FILE):
            try:
                os.remove(LOCAL_FILE)
            except OSError:
                pass
        sheets_handler.use_google = False
        
    def test_01_classify_transaction(self):
        print("\n--- Testing Skill 3: classify_transaction ---")
        
        # Test static rules matching
        res = classify_transaction("Lidl Supermarkt", 25.30)
        self.assertEqual(res["category"], "Lebensmittel")
        self.assertEqual(res["confidence"], 0.99)
        
        res = classify_transaction("dm drogerie", 14.20)
        self.assertEqual(res["category"], "Drogerie")
        self.assertEqual(res["confidence"], 0.99)
        
        res = classify_transaction("HEM Tankstelle", 68.51)
        self.assertEqual(res["category"], "Benzin")
        self.assertEqual(res["confidence"], 0.98)
        
        # Test Amazon special rule (should map to Unbekannt, confidence 0.70 to trigger confirm)
        res = classify_transaction("Amazon Marketplace", 39.99)
        self.assertEqual(res["category"], "Unbekannt")
        self.assertEqual(res["confidence"], 0.70)

    @patch("utils.gemini_client.gemini_client.generate_json")
    def test_02_parse_text(self, mock_gemini):
        print("\n--- Testing Skill 1: parse_text ---")
        
        # Mock Gemini JSON response
        mock_gemini.return_value = {
            "date": "2026-06-24",
            "type": "expense",
            "person": "shared",
            "merchant": "Too Good To Go",
            "amount": 4.00,
            "category_hint": "Lebensmittel",
            "source": "text",
            "note": "Abendessen"
        }
        
        res = parse_text("Heute 4 Euro bei Too Good To Go ausgegeben")
        self.assertEqual(res["merchant"], "Too Good To Go")
        self.assertEqual(res["amount"], 4.00)
        self.assertEqual(res["type"], "expense")
        self.assertEqual(res["person"], "shared")
        self.assertEqual(res["date"], "2026-06-24")

    def test_03_sheets_writer(self):
        print("\n--- Testing Skill 4: write_to_sheets ---")
        tx = {
            "date": "2026-06-24",
            "type": "expense",
            "person": "shared",
            "merchant": "Too Good To Go",
            "amount": 4.00,
            "category": "Lebensmittel",
            "subcategory": "Too Good To Go",
            "source": "text",
            "note": "Abendessen"
        }
        
        success_msg = write_to_sheets(tx)
        print(success_msg)
        self.assertIn("✅ Ich habe die Transaktion per Chat", success_msg)
        
        # Verify file was written locally
        self.assertTrue(os.path.exists(LOCAL_FILE))
        
        # Check sheet rows
        df = sheets_handler.get_transactions("2026-06")
        self.assertFalse(df.empty)
        self.assertEqual(df.iloc[0]["Händler"], "Too Good To Go")
        # Parse float
        self.assertEqual(float(str(df.iloc[0]["Betrag"]).replace(",", ".")), 4.00)

    def test_04_analytics(self):
        print("\n--- Testing Skill 5: generate_analytics ---")
        import pandas as pd
        from skills.analytics import generate_analytics
        
        # Construct sheet_data
        df_exp = pd.DataFrame([
            {"date": "2026-06-05", "merchant": "Lidl", "amount": 84.30, "category": "Lebensmittel", "subcategory": "Supermarkt", "source": "manual", "confidence": 1.0},
            {"date": "2026-06-08", "merchant": "dm drogerie", "amount": 24.15, "category": "Drogerie", "subcategory": "Drogeriebedarf", "source": "manual", "confidence": 1.0}
        ])
        
        df_inc = pd.DataFrame([
            {"date": "2026-06-01", "person": "katja", "category": "Einkommen", "amount": 2800.00, "source": "manual"}
        ])
        
        df_sav = pd.DataFrame([
            {"date": "2026-06-20", "person": "katja", "category": "Investitionen (Sparpläne)", "amount": 300.00, "source": "manual"}
        ])
        
        # Add previous month data for MoM comparison
        df_exp_prev = pd.DataFrame([
            {"date": "2026-05-05", "merchant": "Lidl", "amount": 80.00, "category": "Lebensmittel", "subcategory": "Supermarkt", "source": "manual", "confidence": 1.0}
        ])
        
        sheet_data = {
            "2026-06 expenses": df_exp,
            "2026-06 income": df_inc,
            "2026-06 savings": df_sav,
            "2026-05 expenses": df_exp_prev
        }
        
        res = generate_analytics(sheet_data)
        
        # Verify structure
        self.assertIn("expenses_by_category", res)
        self.assertIn("monthly_totals", res)
        self.assertIn("mom_comparison", res)
        self.assertIn("summary_table", res)
        
        # Verify Lebensmittel expenses in current month
        self.assertEqual(res["expenses_by_category"]["Lebensmittel"], 84.30)
        
        # Verify MoM comparison
        # Lidl in May (80.00) vs June (84.30) -> change_pct is (84.3 - 80) / 80 * 100 = 5.375%
        self.assertEqual(res["mom_comparison"]["Lebensmittel"]["current"], 84.30)
        self.assertEqual(res["mom_comparison"]["Lebensmittel"]["previous"], 80.00)
        self.assertAlmostEqual(res["mom_comparison"]["Lebensmittel"]["change_pct"], 5.37, places=2)
        
        # Verify monthly totals
        totals_june = res["monthly_totals"]["2026-06"]
        self.assertEqual(totals_june["expenses"], 84.30 + 24.15)
        self.assertEqual(totals_june["income"], 2800.00)
        self.assertEqual(totals_june["savings"], 300.00)
        
        # Verify summary table has correct headers/rows
        june_row = [r for r in res["summary_table"] if r["Monat"] == "Juni"][0]
        self.assertEqual(june_row["Einnahmen"], 2800.00)
        self.assertEqual(june_row["Ausgaben"], 84.30 + 24.15)
        self.assertEqual(june_row["Ersparnisse"], 300.00)
        self.assertEqual(june_row["Bilanz"], 2800.00 - (84.30 + 24.15) - 300.00)

    def test_05_correction(self):
        print("\n--- Testing Skill 6: correct_transaction ---")
        
        # Mock Gemini parsing for correction
        with patch("skills.correction.parse_correction_request") as mock_parse:
            mock_parse.return_value = {
                "date": "2026-06-24",
                "merchant": "Too Good To Go",
                "amount": 4.00,
                "new_category": "Restaurant / Café"
            }
            
            res = correct_transaction("Die Too Good To Go Buchung von gestern war Restaurant, nicht Lebensmittel")
            print(res["message"])
            self.assertEqual(res["status"], "success")
            self.assertIn("Kategorie geändert", res["message"])
            
            # Check if category updated in sheet
            df = sheets_handler.get_transactions("2026-06")
            self.assertEqual(df.iloc[0]["Kategorie"], "Restaurant / Café")

    def test_06_pdf_parsing_error_handling(self):
        print("\n--- Testing Skill 2: parse_pdf (Error Handling) ---")
        # Check invalid PDF bytes raises ValueError
        with self.assertRaises(ValueError):
            parse_pdf(b"not a pdf")

    @patch("utils.gemini_client.gemini_client.generate_json")
    def test_07_clarify_pending_transaction(self, mock_gemini):
        print("\n--- Testing Skill 1b: clarify_pending_transaction ---")
        tx = {
            "is_transaction": True,
            "date": "2026-06-25",
            "date_specified": False,
            "merchant": "Lidl",
            "merchant_specified": True,
            "amount": 23.50,
            "amount_specified": True,
            "type": "expense",
            "person": "shared"
        }
        mock_gemini.return_value = {
            "is_transaction": True,
            "date": "2026-05-25",
            "date_specified": True,
            "merchant": "Lidl",
            "merchant_specified": True,
            "amount": 23.50,
            "amount_specified": True,
            "type": "expense",
            "person": "shared",
            "category": "Lebensmittel"
        }
        clarified = clarify_pending_transaction(tx, "für Mai")
        self.assertEqual(clarified["date"], "2026-05-25")
        self.assertTrue(clarified["date_specified"])

    @patch("utils.gemini_client.gemini_client.generate")
    def test_08_generate_general_response(self, mock_gemini):
        print("\n--- Testing general response generation ---")
        mock_gemini.return_value = "Hallo! Ich bin dein Assistent."
        res = generate_general_response("Hallo")
        self.assertIn("Assistent", res)

if __name__ == "__main__":
    unittest.main()
