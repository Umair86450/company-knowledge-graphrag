#!/usr/bin/env bash
# Delete data from the database.
#   ./delete_db.sh session <id>   -> delete one session + its messages
#   ./delete_db.sh user <id>      -> delete one user + all their sessions + messages
#   ./delete_db.sh all            -> delete all data (users, sessions, messages)
set -euo pipefail

DB="$(dirname "$0")/database/chat.db"

if [ ! -f "$DB" ]; then
  echo "Database not found: $DB"
  exit 1
fi

run() { sqlite3 "$DB" "PRAGMA foreign_keys = ON; $1"; }

case "${1:-}" in
  session)
    [ -n "${2:-}" ] || { echo "Usage: ./delete_db.sh session <id>"; exit 1; }
    run "DELETE FROM sessions WHERE id = $2;"
    echo "Session $2 (and its messages) deleted."
    ;;
  user)
    [ -n "${2:-}" ] || { echo "Usage: ./delete_db.sh user <id>"; exit 1; }
    run "DELETE FROM users WHERE id = $2;"
    echo "User $2 (and their sessions + messages) deleted."
    ;;
  all)
    read -r -p "Delete all data? (y/N) " ok
    [ "$ok" = "y" ] || { echo "Cancelled."; exit 0; }
    run "DELETE FROM messages; DELETE FROM sessions; DELETE FROM users; DELETE FROM sqlite_sequence;"
    echo "All data deleted. IDs will start from 1 again."
    ;;
  *)
    echo "Usage:"
    echo "  ./delete_db.sh session <id>"
    echo "  ./delete_db.sh user <id>"
    echo "  ./delete_db.sh all"
    exit 1
    ;;
esac
