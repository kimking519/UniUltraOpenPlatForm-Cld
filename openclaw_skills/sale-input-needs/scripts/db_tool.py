import sqlite3
import sys
import os
import argparse

def query_db(db_path, sql, params=()):
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Database Error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Query UniUltra database from Skill')
    parser.add_argument('--db_path', required=True, help='Path to uni_platform.db')
    parser.add_argument('--action', choices=['find_cli', 'check_mpn', 'raw'], default='find_cli')
    parser.add_argument('--query', help='Search term or raw SQL')
    
    args = parser.parse_args()
    
    if args.action == 'find_cli':
        sql = "SELECT cli_id, cli_name FROM uni_cli WHERE cli_name LIKE ? OR cli_id LIKE ?"
        results = query_db(args.db_path, sql, (f"%{args.query}%", f"%{args.query}%"))
        if results:
            for r in results:
                print(f"ID: {r['cli_id']} | Name: {r['cli_name']}")
        else:
            print("No matching clients found.")
            
    elif args.action == 'raw' and args.query:
        # Dangerous but useful for agentic workflows
        results = query_db(args.db_path, args.query)
        if results:
            import json
            print(json.dumps(results, ensure_ascii=False, indent=2))
            
if __name__ == "__main__":
    main()
