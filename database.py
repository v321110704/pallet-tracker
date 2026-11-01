import os
import sqlite3
from datetime import date, datetime
from typing import Dict, Any, List, Optional
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
IS_POSTGRES = bool(DATABASE_URL and (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")))
if IS_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pallets.db")
def get_connection():
    if IS_POSTGRES:
        url = DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(url)
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
def get_cursor(conn):
    if IS_POSTGRES:
        return conn.cursor(cursor_factory=RealDictCursor)
    else:
        return conn.cursor()
def adapt_sql(sql: str) -> str:
    if IS_POSTGRES:
        return sql.replace("?", "%s")
    return sql
def row_to_dict(row) -> Dict[str, Any]:
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, (datetime, date)):
            d[k] = str(v)
    return d
def init_db():
    conn = get_connection()
    cursor = get_cursor(conn)
    
    if IS_POSTGRES:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key VARCHAR(100) PRIMARY KEY,
            value TEXT
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS production (
            id SERIAL PRIMARY KEY,
            date VARCHAR(20) NOT NULL,
            lyubota INTEGER NOT NULL DEFAULT 0,
            galkin INTEGER NOT NULL DEFAULT 0,
            author VARCHAR(100) DEFAULT 'Користувач',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS shipments (
            id SERIAL PRIMARY KEY,
            date VARCHAR(20) NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            note TEXT DEFAULT '',
            author VARCHAR(100) DEFAULT 'Користувач',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
    else:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            lyubota INTEGER NOT NULL DEFAULT 0,
            galkin INTEGER NOT NULL DEFAULT 0,
            author TEXT DEFAULT 'Користувач',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS shipments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            note TEXT DEFAULT '',
            author TEXT DEFAULT 'Користувач',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
    
    cursor.execute("SELECT value FROM settings WHERE key = 'initial_stock'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO settings (key, value) VALUES ('initial_stock', '0')")
        
    conn.commit()
    conn.close()
def get_initial_stock() -> int:
    conn = get_connection()
    cursor = get_cursor(conn)
    cursor.execute("SELECT value FROM settings WHERE key = 'initial_stock'")
    row = cursor.fetchone()
    conn.close()
    return int(row["value"]) if row else 0
def set_initial_stock(stock: int) -> None:
    conn = get_connection()
    cursor = get_cursor(conn)
    sql = adapt_sql("""
    INSERT INTO settings (key, value) VALUES ('initial_stock', ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """)
    cursor.execute(sql, (str(stock),))
    conn.commit()
    conn.close()
def add_production(date_str: str, lyubota: int, galkin: int, author: str = "Користувач") -> int:
    conn = get_connection()
    cursor = get_cursor(conn)
    if IS_POSTGRES:
        cursor.execute("""
        INSERT INTO production (date, lyubota, galkin, author)
        VALUES (%s, %s, %s, %s) RETURNING id
        """, (date_str, max(0, lyubota), max(0, galkin), author))
        prod_id = cursor.fetchone()["id"]
    else:
        cursor.execute("""
        INSERT INTO production (date, lyubota, galkin, author)
        VALUES (?, ?, ?, ?)
        """, (date_str, max(0, lyubota), max(0, galkin), author))
        prod_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return prod_id
def add_shipment(date_str: str, quantity: int, note: str = "", author: str = "Користувач") -> int:
    conn = get_connection()
    cursor = get_cursor(conn)
    if IS_POSTGRES:
        cursor.execute("""
        INSERT INTO shipments (date, quantity, note, author)
        VALUES (%s, %s, %s, %s) RETURNING id
        """, (date_str, max(0, quantity), note.strip(), author))
        shipment_id = cursor.fetchone()["id"]
    else:
        cursor.execute("""
        INSERT INTO shipments (date, quantity, note, author)
        VALUES (?, ?, ?, ?)
        """, (date_str, max(0, quantity), note.strip(), author))
        shipment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return shipment_id
def delete_shipment(shipment_id: int) -> bool:
    conn = get_connection()
    cursor = get_cursor(conn)
    cursor.execute(adapt_sql("DELETE FROM shipments WHERE id = ?"), (shipment_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted
def delete_production(prod_id: int) -> bool:
    conn = get_connection()
    cursor = get_cursor(conn)
    cursor.execute(adapt_sql("DELETE FROM production WHERE id = ?"), (prod_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted
def get_recent_shipments(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = get_cursor(conn)
    cursor.execute(adapt_sql("""
    SELECT id, date, quantity, note, author, created_at
    FROM shipments
    ORDER BY date DESC, id DESC
    LIMIT ?
    """), (limit,))
    rows = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows
def get_recent_production(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = get_cursor(conn)
    cursor.execute(adapt_sql("""
    SELECT id, date, lyubota, galkin, (lyubota + galkin) as total, author, created_at
    FROM production
    ORDER BY date DESC, id DESC
    LIMIT ?
    """), (limit,))
    rows = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows
def get_stock_summary(target_date: Optional[str] = None) -> Dict[str, Any]:
    if not target_date:
        target_date = date.today().strftime("%Y-%m-%d")
        
    conn = get_connection()
    cursor = get_cursor(conn)
    
    cursor.execute("SELECT value FROM settings WHERE key = 'initial_stock'")
    row = cursor.fetchone()
    initial_stock = int(row["value"]) if row else 0
    
    cursor.execute("SELECT COALESCE(SUM(lyubota), 0) as total_l, COALESCE(SUM(galkin), 0) as total_g FROM production")
    prod_row = cursor.fetchone()
    total_lyubota = int(prod_row["total_l"])
    total_galkin = int(prod_row["total_g"])
    total_produced = total_lyubota + total_galkin
    
    cursor.execute("SELECT COALESCE(SUM(quantity), 0) as total_s FROM shipments")
    ship_row = cursor.fetchone()
    total_shipped = int(ship_row["total_s"])
    
    current_stock = initial_stock + total_produced - total_shipped
    
    cursor.execute(adapt_sql("""
    SELECT COALESCE(SUM(lyubota), 0) as l_today, COALESCE(SUM(galkin), 0) as g_today
    FROM production
    WHERE date = ?
    """), (target_date,))
    today_prod = cursor.fetchone()
    today_l = int(today_prod["l_today"])
    today_g = int(today_prod["g_today"])
    today_total = today_l + today_g
    
    cursor.execute(adapt_sql("SELECT COALESCE(SUM(quantity), 0) as s_today FROM shipments WHERE date = ?"), (target_date,))
    today_shipped = int(cursor.fetchone()["s_today"])
    
    cursor.execute("""
    SELECT DISTINCT date
    FROM production
    WHERE (lyubota > 0 OR galkin > 0)
    ORDER BY date DESC
    LIMIT 15
    """)
    date_rows = cursor.fetchall()
    working_dates = [r["date"] for r in date_rows]
    
    l_15d = 0
    g_15d = 0
    period_start = None
    period_end = None
    
    if working_dates:
        period_end = max(working_dates)
        period_start = min(working_dates)
        placeholders = ",".join(("%s" if IS_POSTGRES else "?") for _ in working_dates)
        cursor.execute(f"""
        SELECT COALESCE(SUM(lyubota), 0) as l_sum, COALESCE(SUM(galkin), 0) as g_sum
        FROM production
        WHERE date IN ({placeholders})
        """, working_dates)
        stats_15 = cursor.fetchone()
        l_15d = int(stats_15["l_sum"])
        g_15d = int(stats_15["g_sum"])
        
    conn.close()
    
    return {
        "pallet_type": "Малі",
        "initial_stock": initial_stock,
        "current_stock": current_stock,
        "total_produced": total_produced,
        "total_shipped": total_shipped,
        "today": {
            "date": target_date,
            "lyubota": today_l,
            "galkin": today_g,
            "total": today_total,
            "shipped": today_shipped
        },
        "stats_15d": {
            "days_count": len(working_dates),
            "period_start": period_start,
            "period_end": period_end,
            "lyubota": l_15d,
            "galkin": g_15d,
            "total": l_15d + g_15d
        }
    }
def generate_report_text(target_date: Optional[str] = None) -> str:
    summary = get_stock_summary(target_date)
    today = summary["today"]
    stats_15 = summary["stats_15d"]
    
    try:
        dt = datetime.strptime(today["date"], "%Y-%m-%d")
        formatted_date = dt.strftime("%d.%m.%Y")
    except Exception:
        formatted_date = today["date"]
        
    p_info = f"({stats_15['days_count']} роб. днів)"
    if stats_15['period_start'] and stats_15['period_end']:
        try:
            d_start = datetime.strptime(stats_15['period_start'], "%Y-%m-%d").strftime("%d.%m")
            d_end = datetime.strptime(stats_15['period_end'], "%Y-%m-%d").strftime("%d.%m")
            p_info = f"({d_start} - {d_end}, {stats_15['days_count']} роб. дн.)"
        except Exception:
            pass
    text = (
        f"📊 ЗВІТ: Піддони (Малі) за {formatted_date}\n"
        f"────────────────────────\n"
        f"🔨 НАБИТО ЗА ДЕНЬ:\n"
        f"  • Любота В.: {today['lyubota']} шт.\n"
        f"  • Галкін В.: {today['galkin']} шт.\n"
        f"  👉 Разом за день: {today['total']} шт.\n\n"
        f"🚚 ВІДВАНТАЖЕНО ЗА ДЕНЬ: {today['shipped']} шт.\n\n"
        f"📦 ЗАГАЛЬНИЙ ОСТАТОК НА СКЛАДІ: {summary['current_stock']} шт.\n"
        f"────────────────────────\n"
        f"📈 НАБИТО ЗА 15 РОБ. ДНІВ {p_info}:\n"
        f"  • Любота В.: {stats_15['lyubota']} шт.\n"
        f"  • Галкін В.: {stats_15['galkin']} шт.\n"
        f"  👉 Всього за 15 днів: {stats_15['total']} шт.\n"
        f"────────────────────────"
    )
    return text
