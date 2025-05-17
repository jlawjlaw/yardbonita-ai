import sys
import pandas as pd

# Get arguments
uuid = sys.argv[1]
outline = sys.argv[2]

# Use the full path to the spreadsheet
file_path = "/Users/justinlaw/Desktop/Yardbonita/file for ai/planning.xlsx"

# Load spreadsheet
df = pd.read_excel(file_path)

# Update the outline for the matching UUID
df.loc[df["uuid"].astype(str) == uuid, "outline"] = outline

# Save the updated spreadsheet
df.to_excel(file_path, index=False)
print(f"✅ Outline inserted for UUID: {uuid}")