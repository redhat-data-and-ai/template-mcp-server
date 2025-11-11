# Fork Sync - Quick Reference

## 🚀 Quick Commands

```bash
# Check for upstream updates
make sync-upstream

# Interactive sync with prompts
./sync-upstream.sh

# Manual sync
git fetch upstream
git merge upstream/main
git push origin main
```

## 📊 Current Configuration

- **Your Fork**: `https://github.com/ramkrsna/template-mcp-server.git`
- **Upstream**: `https://github.com/redhat-data-and-ai/template-mcp-server.git`
- **Current Status**: ✅ In sync with upstream

## 🔄 Typical Workflow

### 1. Before Starting New Work
```bash
make sync-upstream
```

### 2. Create Feature Branch
```bash
git checkout -b feature/my-feature
```

### 3. Make Changes & Test
```bash
# Make your changes
make test
```

### 4. Keep Branch Updated
```bash
git fetch upstream
git rebase upstream/main
```

### 5. Push & Create PR
```bash
git push origin feature/my-feature
```

## ⚠️ Common Issues

### Merge Conflicts
```bash
git status  # See conflicts
# Edit files, resolve conflicts
git add .
git commit
```

### Diverged History
```bash
git fetch upstream
git reset --hard upstream/main  # ⚠️ Loses local changes!
git push origin main --force
```

### Upstream Not Found
```bash
git remote add upstream https://github.com/redhat-data-and-ai/template-mcp-server.git
```

## 📚 More Help

- Full guide: [FORK_MAINTENANCE.md](FORK_MAINTENANCE.md)
- Upstream repo: https://github.com/redhat-data-and-ai/template-mcp-server
- Issues: https://github.com/redhat-data-and-ai/template-mcp-server/issues

