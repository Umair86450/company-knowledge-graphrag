#!/usr/bin/env bash
# Database se data delete karne ke liye.
#   ./delete_db.sh session <id>   -> ek session + uske messages delete
#   ./delete_db.sh user <id>      -> ek user + uski saari sessions + messages delete
#   ./delete_db.sh all            -> saara data delete (users, sessions, messages)
set -euo pipefail

DB="$(dirname "$0")/database/chat.db"

if [ ! -f "$DB" ]; then
  echo "Database nahi mili: $DB"
  exit 1
fi

run() { sqlite3 "$DB" "PRAGMA foreign_keys = ON; $1"; }

case "${1:-}" in
  session)
    [ -n "${2:-}" ] || { echo "Usage: ./delete_db.sh session <id>"; exit 1; }
    run "DELETE FROM sessions WHERE id = $2;"
    echo "Session $2 (aur uske messages) delete ho gaye."
    ;;
  user)
    [ -n "${2:-}" ] || { echo "Usage: ./delete_db.sh user <id>"; exit 1; }
    run "DELETE FROM users WHERE id = $2;"
    echo "User $2 (aur uski sessions + messages) delete ho gaye."
    ;;
  all)
    read -r -p "Sab data delete kar dein? (y/N) " ok
    [ "$ok" = "y" ] || { echo "Cancel."; exit 0; }
    run "DELETE FROM messages; DELETE FROM sessions; DELETE FROM users; DELETE FROM sqlite_sequence;"
    echo "Saara data delete ho gaya. Ab ids 1 se shuru hongi."
    ;;
  *)
    echo "Usage:"
    echo "  ./delete_db.sh session <id>"
    echo "  ./delete_db.sh user <id>"
    echo "  ./delete_db.sh all"
    exit 1
    ;;
esac
