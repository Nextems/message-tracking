import json
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from datetime import datetime
from typing import List
from urllib.parse import unquote

DB_URL = "postgresql://postgres:[YOUR-PASSWORD]@db.syderyofyqrztvqsmmxl.supabase.co:5432/postgres"


def get_connection():
    rest = DB_URL.split("://", 1)[1]
    userinfo, _, netloc = rest.rpartition("@")
    user, _, password = userinfo.partition(":")
    hostport, _, dbname = netloc.partition("/")
    host, _, port = hostport.partition(":")
    return psycopg2.connect(
        host=host or None,
        port=int(port) if port else 5432,
        user=user,
        password=unquote(password),
        dbname=dbname or "postgres",
        connect_timeout=10,
    )


@contextmanager
def db_connect():
    conn = get_connection()
    cur = None
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if cur is not None:
            cur.close()
        conn.close()


def init_db():
    with db_connect() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_stats (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL DEFAULT CURRENT_DATE,
                token_id TEXT NOT NULL,
                token_name TEXT NOT NULL,
                geo TEXT,
                lead INTEGER DEFAULT 0,
                sale INTEGER DEFAULT 0,
                registration INTEGER DEFAULT 0,
                updated_at TEXT,
                UNIQUE(date, token_id, token_name)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS adspower_profiles (
                id SERIAL PRIMARY KEY,
                profile_name TEXT UNIQUE NOT NULL,
                bound_records TEXT
            )
            """
        )


def upsert_stat(token_id: str, token_name: str, event_type: str, geo: str = ""):
    event = event_type.lower().replace(" ", "")
    if event not in ("lead", "sale", "registration"):
        raise ValueError(f"Unknown event_type: {event_type!r}")

    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with db_connect() as cur:
        cur.execute(
            f"""
            INSERT INTO daily_stats (date, token_id, token_name, geo, {event}, updated_at)
            VALUES (%s, %s, %s, %s, 1, %s)
            ON CONFLICT(date, token_id, token_name) DO UPDATE SET
                {event} = daily_stats.{event} + EXCLUDED.{event},
                updated_at = EXCLUDED.updated_at,
                geo = COALESCE(EXCLUDED.geo, daily_stats.geo)
            """,
            (today, token_id, token_name, geo, now),
        )


def get_unique_geos():
    with db_connect() as cur:
        cur.execute(
            """
            SELECT DISTINCT geo
            FROM daily_stats
            WHERE geo IS NOT NULL AND geo != ''
            ORDER BY geo
            """
        )
        rows = cur.fetchall()
    return [r["geo"] for r in rows]


def get_no_id_records(date_str=None):
    query = """
        SELECT * FROM daily_stats
        WHERE token_id IS NULL OR token_id = ''
    """
    params: List = []
    if date_str:
        query += " AND date = %s"
        params.append(date_str)
    query += " ORDER BY date DESC, id DESC"

    with db_connect() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    return rows


def get_records_by_date(date_str):
    with db_connect() as cur:
        cur.execute(
            """
            SELECT * FROM daily_stats
            WHERE date = %s
            ORDER BY id DESC
            """,
            (str(date_str),),
        )
        rows = cur.fetchall()
    return rows


def delete_record(record_id):
    with db_connect() as cur:
        cur.execute(
            "DELETE FROM daily_stats WHERE id = %s",
            (record_id,),
        )
        return cur.rowcount


def get_keitaro_prefixes(delimiter="_"):
    with db_connect() as cur:
        cur.execute("SELECT DISTINCT token_name FROM daily_stats")
        rows = cur.fetchall()

    prefixes = set()
    for row in rows:
        name = (row["token_name"] or "").strip()
        if not name:
            continue
        positions = []
        for sep in (delimiter, "-"):
            idx = name.find(sep)
            if idx != -1:
                positions.append(idx)
        cut = min(positions) if positions else -1
        prefix = name if cut == -1 else name[:cut]
        if prefix:
            prefixes.add(prefix)
    return sorted(prefixes)


def get_all_profiles():
    with db_connect() as cur:
        cur.execute(
            """
            SELECT id, profile_name, bound_records
            FROM adspower_profiles
            ORDER BY profile_name
            """
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def get_profile_by_name(profile_name):
    with db_connect() as cur:
        cur.execute(
            """
            SELECT id, profile_name, bound_records
            FROM adspower_profiles
            WHERE profile_name = %s
            """,
            (profile_name,),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def update_profile(old_name, new_name, bound_records):
    if isinstance(bound_records, (list, tuple)):
        payload = json.dumps(list(bound_records), ensure_ascii=False)
    else:
        payload = bound_records
    with db_connect() as cur:
        cur.execute(
            """
            UPDATE adspower_profiles
            SET profile_name = %s, bound_records = %s
            WHERE profile_name = %s
            """,
            (new_name, payload, old_name),
        )
        return cur.rowcount


def delete_profile(profile_name):
    with db_connect() as cur:
        cur.execute(
            """
            DELETE FROM adspower_profiles
            WHERE profile_name = %s
            """,
            (profile_name,),
        )
        return cur.rowcount


def get_records_by_profile(profile_name):
    profile = get_profile_by_name(profile_name)
    if not profile:
        return []
    raw = profile.get("bound_records") or "[]"
    try:
        bound = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        bound = []
    if not isinstance(bound, list):
        bound = []

    ids, names = set(), set()
    for rec in bound:
        if isinstance(rec, dict):
            value_id = rec.get("token_id") or rec.get("id")
            value_name = rec.get("token_name") or rec.get("name")
            if value_id:
                ids.add(str(value_id))
            if value_name:
                names.add(str(value_name))
        elif isinstance(rec, (int, float)):
            ids.add(str(rec))
        else:
            token = str(rec).strip()
            if not token:
                continue
            (ids if token.isdigit() else names).add(token)

    if not ids and not names:
        return []

    with db_connect() as cur:
        if ids:
            id_ph = ",".join("%s" for _ in ids)
            query = f"""
                SELECT * FROM daily_stats
                WHERE token_id IN ({id_ph})
            """
            params = tuple(ids)
            if names:
                name_ph = ",".join("%s" for _ in names)
                query += f" OR token_name IN ({name_ph})"
                params += tuple(names)
        else:
            name_ph = ",".join("%s" for _ in names)
            query = f"""
                SELECT * FROM daily_stats
                WHERE token_name IN ({name_ph})
            """
            params = tuple(names)
        query += " ORDER BY date DESC, id DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
    return rows


def search_records(query, search_by="name"):
    column = "token_name" if search_by == "name" else "token_id"
    like = f"%{query}%"
    with db_connect() as cur:
        cur.execute(
            f"""
            SELECT * FROM daily_stats
            WHERE {column} LIKE %s
            ORDER BY date DESC, id DESC
            """,
            (like,),
        )
        rows = cur.fetchall()
    return rows


def save_adspower_profile(profile_name: str, bound_records_list):
    if isinstance(bound_records_list, (list, tuple)):
        payload = json.dumps(list(bound_records_list), ensure_ascii=False)
    else:
        payload = bound_records_list
    with db_connect() as cur:
        cur.execute(
            """
            INSERT INTO adspower_profiles (profile_name, bound_records)
            VALUES (%s, %s)
            ON CONFLICT(profile_name) DO UPDATE SET
                bound_records = EXCLUDED.bound_records
            """,
            (profile_name, payload),
        )


if __name__ == "__main__":
    init_db()

    # ---- Validation test: insert a record with empty token_id ----
    success = False
    try:
        upsert_stat(token_id="", token_name="TestProfile", event_type="Lead", geo="UA")
        no_id = get_no_id_records()
        assert len(no_id) > 0, "Expected at least one NO ID record"
        assert all(r["token_id"] in ("", None) for r in no_id)
        success = True
        print(f"OK: {len(no_id)} record(s) without ID; NULL/empty handled without exceptions.")
    except Exception as exc:
        print(f"ERROR: {exc}")
    finally:
        if not success:
            raise SystemExit(1)
