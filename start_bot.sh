#!/bin/bash
# Auto-restart wrapper for the Telegram userbot
# This script will restart the bot if it crashes or exits unexpectedly

echo "Starting Telegram Story Userbot with auto-restart..."

while true; do
    echo ""
    echo "========================================"
    echo "Starting bot at $(date)"
    echo "========================================"

    # Run the bot
    python bot.py
    EXIT_CODE=$?

    echo ""
    echo "Bot exited with code: $EXIT_CODE at $(date)"

    # If exit code is 0 (clean shutdown), don't restart
    if [ $EXIT_CODE -eq 0 ]; then
        echo "Bot exited cleanly. Not restarting."
        break
    fi

    # Check if exit is due to keyboard interrupt (130)
    if [ $EXIT_CODE -eq 130 ]; then
        echo "Keyboard interrupt detected. Not restarting."
        break
    fi

    echo "Bot crashed. Waiting 10 seconds before restart..."
    sleep 10
done

echo "Bot stopped completely."
