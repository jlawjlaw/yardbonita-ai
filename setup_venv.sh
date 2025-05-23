#!/bin/bash

# Change this path if needed
ENV_DIR="myenv"

echo "🔄 Setting up virtual environment in '$ENV_DIR'..."

# Step 1: Create the virtual environment
python3 -m venv "$ENV_DIR"

# Step 2: Activate it
source "$ENV_DIR/bin/activate"

# Step 3: Upgrade pip safely
python -m pip install --upgrade pip

# Step 4: Install requirements
if [ -f "requirements.txt" ]; then
    echo "📦 Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "⚠️ requirements.txt not found. Skipping install."
fi

echo "✅ Environment setup complete. You are now in '$ENV_DIR'"
echo "To activate it later: source $ENV_DIR/bin/activate"