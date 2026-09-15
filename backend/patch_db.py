def update_session_title(session_id: str, new_title: str) -> bool:
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE sessions SET title = %s, updated_at = NOW() WHERE id = %s RETURNING id;", (new_title, session_id))
        updated = cur.fetchone()
    conn.close()
    return bool(updated)
