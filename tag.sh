#!/bin/bash

# Prompt for version tag
read -p "Enter new version tag (e.g. v1.0.6): " VERSION

# Validate format
if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "❌ Version tag must follow format vX.Y.Z"
  exit 1
fi

VERSION_NUM=${VERSION#v}  # Remove leading "v"

# Check if tag exists
if git rev-parse "$VERSION" >/dev/null 2>&1; then
  echo "❌ Tag $VERSION already exists."
  exit 1
fi

# Update VERSION.txt
echo "$VERSION" > VERSION.txt
echo "📄 VERSION.txt updated to $VERSION"

# Search and update all Python files with __version__
echo "🔍 Scanning Python files for __version__ string..."
PY_FILES=$(grep -rl '__version__ = ' . --include="*.py")

for file in $PY_FILES; do
  sed -i '' "s/__version__ = \".*\"/__version__ = \"$VERSION_NUM\"/" "$file"
  echo "📝 Updated $file"
done

# Commit, tag, push
git add .
git commit -m "🔖 Version $VERSION"
git tag -a "$VERSION" -m "Version $VERSION"
git push
git push origin "$VERSION"

echo "✅ Tagged and pushed $VERSION successfully."