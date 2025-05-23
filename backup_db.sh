#!/bin/bash

# === CONFIGURATION ===
SOURCE_DB="/Users/justinlaw/Desktop/Yardbonita/file for AI/yardbonita.db"
DEST_DIR="$HOME/Library/CloudStorage/GoogleDrive-justinlaw@gmail.com/YardBonitaBackups"

# === EXECUTION ===
TIMESTAMP=$(date +%Y-%m-%d_%H-%M)
DEST_FILE="$DEST_DIR/yardbonita_$TIMESTAMP.db"

echo "🔄 Backing up to $DEST_FILE..."
cp "$SOURCE_DB" "$DEST_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Backup complete."
else
    echo "❌ Backup failed."
fi