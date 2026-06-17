#!/usr/bin/env bash
# Database dekhne ke liye: ./show_db.sh           -> users, sessions, message counts
#                          ./show_db.sh <session> -> us session ki poori chat history
set -euo pipefail

DB="$(dirname "$0")/database/chat.db"

if [ ! -f "$DB" ]; then
  echo "Database nahi mili: $DB"
  exit 1
fi

if [ "$#" -ge 1 ]; then
  echo "=== SESSION $1 — MESSAGES ==="
  sqlite3 -header -column "$DB" \
    "SELECT id, role, content, created_at FROM messages WHERE session_id = $1 ORDER BY id;"
  exit 0
fi

echo "=== USERS ==="
sqlite3 -header -column "$DB" "SELECT * FROM users;"

echo
echo "=== SESSIONS ==="
sqlite3 -header -column "$DB" \
  "SELECT s.id, u.username, s.claude_session_id, s.created_at
   FROM sessions s JOIN users u ON u.id = s.user_id
   ORDER BY s.id;"

echo
echo "=== MESSAGES PER SESSION ==="
sqlite3 -header -column "$DB" \
  "SELECT session_id, COUNT(*) AS messages FROM messages GROUP BY session_id ORDER BY session_id;"
