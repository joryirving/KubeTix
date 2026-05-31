# Contributing to KubeTix

Contributions welcome! Feel free to open issues or submit PRs.

## Dependency Updates

### Renovate Configuration

This repository uses [Renovate](https://docs.renovatebot.com/) for automated dependency updates, configured via `.renovaterc.json5` extending the shared [`misospace/renovate-config`](https://github.com/misospace/renovate-config).

Automerge is enabled for:
- **GitHub Actions** — minor, patch, and digest updates (trusted actions merge within 1 minute; others after 3 days)
- **Branch updates** — via `:automergeBranch` preset

### SLA

Dependency update PRs created by Renovate are auto-merged per the rules above. No manual merge is required for standard dependency updates. For major version bumps, the dependency dashboard is monitored weekly to review and approve upgrades.
