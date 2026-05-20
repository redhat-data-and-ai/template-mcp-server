# Rate Limiting Configuration Guide

This document describes all configurable aspects of the rate limiting middleware.

## ✅ What's Configurable

### Core Rate Limiting Settings

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `RATE_LIMIT_ENABLED` | `True` | boolean | Enable/disable rate limiting globally |
| `RATE_LIMIT_REQUESTS` | `100` | 1-10000 | Maximum requests allowed per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | 1-3600 | Time window in seconds (1s to 1hr) |
| `RATE_LIMIT_STORAGE_TYPE` | `memory` | memory, postgresql | Storage backend selection |
| `RATE_LIMIT_EXCLUDE_PATHS` | `["/health", "/docs", ...]` | list | Paths excluded from rate limiting |

### Advanced Settings

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `RATE_LIMIT_CLEANUP_INTERVAL_SECONDS` | `60` | 10-3600 | How often cleanup runs (in seconds) |
| `RATE_LIMIT_MEMORY_RETENTION_SECONDS` | `3600` | 60-86400 | How long to keep inactive clients in memory |
| `RATE_LIMIT_DB_RETENTION_HOURS` | `24` | 1-168 | How long to keep records in PostgreSQL (in hours) |

## 🚫 What's NOT Configurable (And Why)

### Fixed by Design

| Item | Value | Reason |
|------|-------|--------|
| HTTP Status Code | `429` | HTTP standard (RFC 6585) |
| Error Message | "Rate limit exceeded" | Standard user-facing message |
| Header Names | `X-RateLimit-*`, `Retry-After` | Industry standard (RFC 6585, GitHub API) |
| Client ID Format | `token:hash` or `ip:address` | Internal implementation detail |
| Sliding Window Algorithm | Fixed | Production-proven algorithm |

### Standard Headers (RFC Compliant)

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1779265264
Retry-After: 30
```

These follow industry standards from:
- RFC 6585 (Additional HTTP Status Codes)
- GitHub API, Twitter API, Stripe API conventions

## 📝 Configuration Examples

### Example 1: Strict Rate Limiting (API Protection)

```bash
# .env
RATE_LIMIT_ENABLED=True
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_STORAGE_TYPE=postgresql
```

**Use case**: Public API with strict limits (30 req/min)

### Example 2: Lenient Rate Limiting (Development)

```bash
# .env
RATE_LIMIT_ENABLED=True
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_STORAGE_TYPE=memory
```

**Use case**: Development environment with high limits

### Example 3: Burst Protection

```bash
# .env
RATE_LIMIT_ENABLED=True
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW_SECONDS=10
RATE_LIMIT_STORAGE_TYPE=memory
```

**Use case**: Protect against rapid bursts (10 req per 10 seconds)

### Example 4: Distributed Deployment

```bash
# .env
RATE_LIMIT_ENABLED=True
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_STORAGE_TYPE=postgresql
RATE_LIMIT_DB_RETENTION_HOURS=48
```

**Use case**: Multiple server instances sharing rate limit state

### Example 5: Custom Excluded Paths

```bash
# .env
RATE_LIMIT_ENABLED=True
RATE_LIMIT_EXCLUDE_PATHS=["/health","/metrics","/status","/internal/debug"]
```

**Use case**: Custom monitoring/internal endpoints

### Example 6: Aggressive Cleanup

```bash
# .env
RATE_LIMIT_CLEANUP_INTERVAL_SECONDS=30
RATE_LIMIT_MEMORY_RETENTION_SECONDS=1800  # 30 minutes
```

**Use case**: High-traffic server with memory constraints

## 🔧 Tuning Guidelines

### For High-Traffic Applications

- Use **PostgreSQL storage** for persistence and distribution
- Increase **cleanup interval** (e.g., 120s) to reduce overhead
- Decrease **retention times** to save memory/disk space

```bash
RATE_LIMIT_STORAGE_TYPE=postgresql
RATE_LIMIT_CLEANUP_INTERVAL_SECONDS=120
RATE_LIMIT_MEMORY_RETENTION_SECONDS=1800
RATE_LIMIT_DB_RETENTION_HOURS=12
```

### For Low-Traffic Applications

- Use **in-memory storage** for simplicity
- Lower **cleanup interval** for responsiveness
- Higher **retention times** to preserve data

```bash
RATE_LIMIT_STORAGE_TYPE=memory
RATE_LIMIT_CLEANUP_INTERVAL_SECONDS=30
RATE_LIMIT_MEMORY_RETENTION_SECONDS=7200
```

### For Testing/Development

- **Disable** or set very high limits
- Use **in-memory** storage

```bash
RATE_LIMIT_ENABLED=False
# OR
RATE_LIMIT_REQUESTS=10000
RATE_LIMIT_WINDOW_SECONDS=60
```

## 🎯 Client Identification

The middleware automatically identifies clients using:

1. **When `ENABLE_AUTH=True`**:
   - Uses hashed authorization token
   - Format: `token:abc123...` (SHA256 hash, first 16 chars)
   - Each unique token gets separate rate limit

2. **When `ENABLE_AUTH=False`**:
   - Uses client IP address
   - Format: `ip:192.168.1.1`
   - All requests from same IP share rate limit

**This is NOT configurable** as it's tied to the authentication system.

## 📊 Validation Rules

Settings are validated on startup:

```python
# Port validation in settings.py
if settings.RATE_LIMIT_ENABLED:
    # Storage type must be valid
    valid_storage = ["memory", "postgresql"]

    # PostgreSQL requires ENABLE_AUTH=True
    if storage == "postgresql" and not ENABLE_AUTH:
        # Falls back to memory with warning

    # Numeric ranges enforced
    assert 1 <= RATE_LIMIT_REQUESTS <= 10000
    assert 1 <= RATE_LIMIT_WINDOW_SECONDS <= 3600
    assert 10 <= RATE_LIMIT_CLEANUP_INTERVAL_SECONDS <= 3600
    assert 60 <= RATE_LIMIT_MEMORY_RETENTION_SECONDS <= 86400
    assert 1 <= RATE_LIMIT_DB_RETENTION_HOURS <= 168
```

## 🔒 Security Considerations

### Token Hashing
- Authorization tokens are hashed (SHA256) before storage
- Only first 16 characters stored for identification
- Original tokens never logged or persisted

### Information Disclosure
- Error messages don't reveal internal details
- Headers show limits but not other clients' usage
- Logs show hashed client IDs, not raw tokens

## 📈 Performance Impact

| Storage | Latency | Memory | Disk | Distribution |
|---------|---------|--------|------|--------------|
| Memory  | ~0.1ms  | ~100 bytes/request | None | Single instance |
| PostgreSQL | ~1-5ms | Minimal | ~50 bytes/request | Multi-instance |

**Recommendation**: Use in-memory for < 10k req/min single instance, PostgreSQL for distributed or high-volume.

## ✅ Summary

**Fully Configurable**:
- ✅ Rate limits (requests, window)
- ✅ Storage backend
- ✅ Excluded paths
- ✅ Cleanup intervals
- ✅ Retention periods
- ✅ Enable/disable globally

**Standards-Based (Fixed)**:
- 🔒 HTTP status codes
- 🔒 Response headers
- 🔒 Error messages
- 🔒 Client ID format

**Zero hard-coded magic numbers or strings** - everything is either configurable or follows industry standards!
