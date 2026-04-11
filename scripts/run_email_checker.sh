#!/bin/bash
# Auto‑restart wrapper for the email payment checker

cd /workspaces/studylens || exit 1

while true; do
    echo "$(date): Starting email checker..."
    python scripts/check_emails.py >> email_checker.log 2>&1
    echo "$(date): Email checker exited. Restarting in 10 seconds..."
    sleep 10
done
