#!/bin/bash
#
# Sync fork with upstream repository
# Usage: ./sync-upstream.sh
#

set -e

echo "🔄 Syncing fork with upstream..."

# Fetch latest changes from upstream
echo "📥 Fetching upstream changes..."
git fetch upstream

# Check if there are any changes
CHANGES=$(git rev-list --count main..upstream/main)

if [ "$CHANGES" -eq 0 ]; then
    echo "✅ Your fork is already up to date with upstream!"
    exit 0
fi

echo "📊 Found $CHANGES new commit(s) in upstream"

# Show what will be merged
echo ""
echo "📋 Changes to be merged:"
git log --oneline --graph main..upstream/main

echo ""
read -p "Do you want to merge these changes? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Merge upstream/main into main
    echo "🔀 Merging upstream/main into main..."
    git merge upstream/main --no-edit
    
    echo "✅ Merge successful!"
    echo ""
    echo "📤 To push changes to your fork, run:"
    echo "   git push origin main"
else
    echo "❌ Merge cancelled"
    exit 1
fi

