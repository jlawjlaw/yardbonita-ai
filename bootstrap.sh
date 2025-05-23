# Move to project dir
cd "$HOME/Desktop/Yardbonita/file for AI"

# Tell pyenv to use Python 3.11.9
pyenv install 3.11.9 --skip-existing
pyenv local 3.11.9

# Double-check it's active
python --version  # ✅ Should say Python 3.11.9

# Recreate the venv with the right Python
rm -rf myenv
python -m venv myenv
source myenv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# ✅ Confirm version inside venv
python --version  # Should still say 3.11.9