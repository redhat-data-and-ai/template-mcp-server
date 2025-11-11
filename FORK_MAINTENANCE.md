# Fork Maintenance Guide

This document describes how to keep your fork of `template-mcp-server` in sync with the upstream repository at https://github.com/redhat-data-and-ai/template-mcp-server.

## Quick Start

### Check for Updates

```bash
# Using Make (recommended)
make sync-upstream

# Or using the sync script
./sync-upstream.sh

# Or manually
git fetch upstream
git log --oneline HEAD..upstream/main
```

### Sync Your Fork

```bash
# Interactive sync (recommended for first-time users)
./sync-upstream.sh

# Or manually
git fetch upstream
git merge upstream/main
git push origin main
```

## Setup (Already Done!)

Your fork is already configured with the upstream remote:

- **Origin**: `https://github.com/ramkrsna/template-mcp-server.git` (your fork)
- **Upstream**: `https://github.com/redhat-data-and-ai/template-mcp-server.git` (original repo)

If you ever need to reconfigure, run:

```bash
git remote add upstream https://github.com/redhat-data-and-ai/template-mcp-server.git
```

## Syncing Strategies

### 1. Simple Merge (Recommended for Clean Forks)

When you haven't made custom changes:

```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

### 2. Rebase (For Clean History)

When you want to keep your commits on top:

```bash
git fetch upstream
git checkout main
git rebase upstream/main
git push origin main --force-with-lease
```

⚠️ **Warning**: Only use rebase if you understand the implications and haven't shared your branch.

### 3. Merge with Custom Changes

When you have custom modifications:

```bash
git fetch upstream
git checkout main
git merge upstream/main
# Resolve any conflicts if they occur
git push origin main
```

## Handling Merge Conflicts

If you encounter conflicts during sync:

1. **Identify conflicts:**
   ```bash
   git status
   ```

2. **Resolve conflicts manually:**
   - Open conflicted files in your editor
   - Look for conflict markers: `<<<<<<<`, `=======`, `>>>>>>>`
   - Choose which changes to keep or merge them manually
   - Remove conflict markers

3. **Mark as resolved:**
   ```bash
   git add <resolved-file>
   ```

4. **Complete the merge:**
   ```bash
   git commit
   git push origin main
   ```

## Best Practices

### 1. Keep Main Clean

- Keep your `main` branch as close to upstream as possible
- Create feature branches for custom modifications:
  ```bash
  git checkout -b feature/my-custom-tool
  ```

### 2. Regular Syncing

Sync regularly to avoid large merge conflicts:

```bash
# Weekly or bi-weekly
make sync-upstream
```

### 3. Document Custom Changes

If you make custom modifications:
- Document them in a `CUSTOM_CHANGES.md` file
- Use clear commit messages
- Consider contributing them back to upstream

### 4. Test After Syncing

Always test after syncing:

```bash
# Run tests
make test

# Or manually
pytest

# Try running the server
make local
```

## Automated Syncing with GitHub Actions

You can set up automated upstream syncing using GitHub Actions. Create `.github/workflows/sync-upstream.yml`:

```yaml
name: Sync with Upstream

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday at midnight
  workflow_dispatch:  # Allow manual trigger

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          fetch-depth: 0

      - name: Sync upstream changes
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git remote add upstream https://github.com/redhat-data-and-ai/template-mcp-server.git
          git fetch upstream
          git checkout main
          git merge upstream/main --no-edit
          git push origin main
```

## Contributing Back to Upstream

If you've made improvements, consider contributing them back:

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/awesome-improvement
   ```

2. **Make your changes and test:**
   ```bash
   # Make changes
   make test
   pre-commit run --all-files
   ```

3. **Push to your fork:**
   ```bash
   git push origin feature/awesome-improvement
   ```

4. **Create a Pull Request:**
   - Go to https://github.com/redhat-data-and-ai/template-mcp-server
   - Click "New Pull Request"
   - Select "compare across forks"
   - Choose your fork and branch

## Troubleshooting

### Upstream Remote Not Found

```bash
git remote add upstream https://github.com/redhat-data-and-ai/template-mcp-server.git
```

### Diverged Branches

If branches have diverged significantly:

```bash
# See the difference
git log --oneline --graph --all --decorate

# Force sync (⚠️ loses your changes)
git reset --hard upstream/main
git push origin main --force
```

### Merge Tool

For complex conflicts, use a merge tool:

```bash
# Configure merge tool (e.g., VS Code)
git config --global merge.tool vscode
git config --global mergetool.vscode.cmd 'code --wait --merge $REMOTE $LOCAL $BASE $MERGED'

# Use it during conflicts
git mergetool
```

## Monitoring Upstream Changes

### GitHub Watch

- Go to https://github.com/redhat-data-and-ai/template-mcp-server
- Click "Watch" → "Custom" → Select "Releases" and "Issues"

### RSS Feed

Subscribe to the releases feed:
```
https://github.com/redhat-data-and-ai/template-mcp-server/releases.atom
```

### GitHub CLI

```bash
# Install gh CLI
brew install gh

# Watch for releases
gh release list --repo redhat-data-and-ai/template-mcp-server
```

## Summary

Your fork is now configured to easily sync with upstream. Use these commands regularly:

```bash
# Check for updates
make sync-upstream

# Sync and merge
./sync-upstream.sh

# Run tests after sync
make test
```

For questions or issues, refer to the upstream repository's documentation or open an issue.

