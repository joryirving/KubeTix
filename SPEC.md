# KubeContext Manager - Project Spec

## Overview
A simple service for sharing temporary Kubernetes access with expiry and audit trails.

## Core Features (MVP)

### 1. Generate Temporary Context
- Upload kubeconfig or connect to cloud provider (AWS EKS, GCP GKE, Azure AKS)
- Select namespace(s) and role (view, edit, admin)
- Set expiry (1h, 4h, 24h, custom)
- Generate shareable link or download temporary context

### 2. Access Management
- Dashboard showing active grants
- Revoke access anytime
- View audit log (who accessed what, when)

### 3. CLI Tool
```bash
# Generate temporary access
kc-share create --cluster prod --role edit --expiry 4h

# Share with team
kc-share share --link --slack

# Check active grants
kc-share list
```

## Tech Stack

### Backend
- **Language**: Python (FastAPI) or Go
- **Database**: SQLite (MVP) → PostgreSQL (scale)
- **Auth**: OAuth2 (GitHub, Google, SSO for teams)
- **Storage**: Encrypted kubeconfig blobs

### Frontend
- **Framework**: Next.js or simple React
- **UI**: Tailwind CSS + shadcn/ui

### Infrastructure
- **Deploy**: Docker + Kubernetes (obviously)
- **CI/CD**: GitHub Actions
- **Hosting**: VPS or cloud (start with DigitalOcean droplet)

## MVP Scope (Weekend Build)

### Week 1: Core
- [ ] CLI tool: `kc-share create` (upload kubeconfig → encrypted blob)
- [ ] Simple web UI: list active grants, revoke
- [ ] Expiry cleanup cron job
- [ ] Basic auth (email + magic link)

### Week 2: Polish
- [ ] Cloud provider integrations (EKS/GKE/AKS)
- [ ] Audit logging
- [ ] Slack/Teams bot integration
- [ ] Team features (multiple users, shared clusters)

## Monetization

### Free Tier
- 1 cluster
- Unlimited temporary grants
- 7-day audit history

### Pro ($9/mo)
- 5 clusters
- SSO/SAML
- 30-day audit history
- Slack/Teams integration

### Team ($29/mo)
- Unlimited clusters
- Full audit logs
- Custom roles
- Priority support

## Next Steps

1. **Validate demand**: Post on r/kubernetes, Hacker News, K8s Slack
2. **Build MVP**: CLI tool first (easiest to ship)
3. **Launch**: Product Hunt + indie hacker communities
4. **Iterate**: Add features based on feedback

## Risks
- Security concerns (handling kubeconfigs)
- Competition (existing IAM solutions)
- Adoption friction (why switch from manual?)

## Differentiation
- Simplicity (no enterprise bloat)
- Speed (instant access, no ticket queue)
- Price (way cheaper than full IAM)
