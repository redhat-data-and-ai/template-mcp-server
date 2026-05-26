# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, report them via one of the following methods:

1. **GitHub Security Advisories**: Use the [Report a vulnerability](https://github.com/redhat-data-and-ai/template-mcp-server/security/advisories/new) button on the Security tab.
2. **Email**: Send details to the repository maintainers listed in [CODEOWNERS](CODEOWNERS).

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Potential impact
- Suggested fix (if any)

### Response Timeline

| Action | Timeframe |
|--------|-----------|
| Acknowledgment | 48 hours |
| Initial assessment | 5 business days |
| Fix or mitigation | Best effort, depends on severity |

### Severity Levels

| Level | Description | Response |
|-------|-------------|----------|
| **Critical** | Remote code execution, data exfiltration | Immediate patch |
| **High** | Authentication bypass, privilege escalation | Patch within 7 days |
| **Medium** | Information disclosure, denial of service | Patch within 30 days |
| **Low** | Minor issues, hardening improvements | Next scheduled release |

## Security Best Practices for Contributors

- Never commit secrets, credentials, or API keys.
- Use environment variables for all sensitive configuration (see `.env.example`).
- Keep dependencies up to date (Dependabot is configured for this).
- All PRs run Bandit security scanning automatically.
- Follow the principle of least privilege in OAuth and storage implementations.

## Disclosure Policy

We follow [responsible disclosure](https://en.wikipedia.org/wiki/Responsible_disclosure). Once a fix is available, we will:

1. Publish a GitHub Security Advisory.
2. Release a patched version.
3. Credit the reporter (unless they prefer anonymity).
