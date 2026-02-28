import sys
import requests
import argparse
import sqlite3
import uuid
import os
from datetime import datetime

def resolve_cli_id(db_path, cli_name_or_id):
    if not os.path.exists(db_path):
        return cli_name_or_id
    try:
        conn = sqlite3.connect(db_path)
        # Try finding by ID first
        row = conn.execute("SELECT cli_id FROM uni_cli WHERE cli_id = ?", (cli_name_or_id,)).fetchone()
        if row: return row[0]
        # Try finding by Name (fuzzy)
        row = conn.execute("SELECT cli_id FROM uni_cli WHERE cli_name LIKE ? LIMIT 1", (f"%{cli_name_or_id}%",)).fetchone()
        conn.close()
        if row: return row[0]
    except: pass
    return cli_name_or_id

def perform_db_input(db_path, cli_id, mpn, brand='', qty=0, price=0.0, remark=''):
    try:
        conn = sqlite3.connect(db_path)
        u_hex = uuid.uuid4().hex
        quote_id = "Q" + datetime.now().strftime("%Y%m%d%H%M%S") + u_hex[:4]
        quote_date = datetime.now().strftime("%Y-%m-%d")
        
        sql = """
        INSERT INTO uni_quote (quote_id, quote_date, cli_id, inquiry_mpn, quoted_mpn, inquiry_brand, inquiry_qty, target_price_rmb, cost_price_rmb, remark)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (quote_id, quote_date, cli_id, mpn.upper().strip(), '', brand, qty, price, 0.0, remark)
        
        conn.execute(sql, params)
        conn.commit()
        conn.close()
        return True, quote_id
    except Exception as e:
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description='Auto input sales needs to UniUltra Platform')
    parser.add_argument('--cli_name', help='Client Name or ID')
    parser.add_argument('--mpn', help='MPN (e.g. TPS54331DR)')
    parser.add_argument('--qty', type=int, default=0)
    parser.add_argument('--brand', default='')
    parser.add_argument('--price', type=float, default=0.0)
    parser.add_argument('--remark', default='')
    parser.add_argument('--db_path', default='uni_platform.db', help='Path to uni_platform.db')
    parser.add_argument('--text', help='Batch text to process (format: MPN QTY BRAND REMARK)')

    args = parser.parse_args()

    # If text is provided, try to parse multiple lines
    if args.text:
        lines = args.text.strip().split('\n')
        print(f"Processing {len(lines)} lines from text...")
        for line in lines:
            parts = line.split() # MPN QTY ...
            if len(parts) >= 1:
                mpn = parts[0]
                qty = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                ok, qid = perform_db_input(args.db_path, args.cli_name or 'C001', mpn, qty=qty)
                if ok: print(f"Added: {mpn} -> {qid}")
                else: print(f"Failed {mpn}: {qid}")
        return

    # Single entry mode
    if not args.mpn:
        print("Error: --mpn is required for single entry mode.")
        return

    cli_id = resolve_cli_id(args.db_path, args.cli_name or 'C001')
    ok, res = perform_db_input(args.db_path, cli_id, args.mpn, args.brand, args.qty, args.price, args.remark)
    
    if ok:
        print(f"Successfully recorded demand. ID: {res}")
    else:
        print(f"Input failed: {res}")

if __name__ == "__main__":
    main()
