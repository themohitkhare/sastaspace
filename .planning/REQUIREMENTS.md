# Requirements: SastaSpace

**Defined:** 2026-03-21
**Core Value:** Users see a stunning AI redesign of their own website and immediately want to hire you.

## v2 Requirements

Requirements for production ship. Each maps to roadmap phases.

### Docker

- [ ] **DOCK-01**: `docker compose up` starts backend (FastAPI), frontend (Next.js), and claude-code-api gateway as separate containers
- [ ] **DOCK-02**: Backend container includes Playwright and Chromium for website crawling
- [ ] **DOCK-03**: Frontend container builds Next.js in production mode and serves via `next start`
- [ ] **DOCK-04**: Containers share a Docker network so frontend can reach backend and backend can reach claude-code-api
- [ ] **DOCK-05**: Environment variables are configured via `.env` file and docker-compose env_file directive
- [ ] **DOCK-06**: Health checks verify each service is responsive before marking container healthy
- [ ] **DOCK-07**: Sites directory is persisted via Docker volume so redesigns survive container restarts

### Testing

- [ ] **TEST-01**: E2E Playwright test loads landing page and verifies hero section, URL input, and how-it-works section render
- [ ] **TEST-02**: E2E test submits an invalid URL and verifies inline validation error appears
- [ ] **TEST-03**: E2E test submits a valid URL and verifies progress view appears with step indicators
- [ ] **TEST-04**: E2E test verifies result page renders with iframe preview and contact form
- [ ] **TEST-05**: E2E test verifies contact form validation (empty submit shows errors)
- [ ] **TEST-06**: E2E tests run in Docker via `docker compose run tests` or equivalent

### Feature Flags

- [ ] **FLAG-01**: `NEXT_PUBLIC_ENABLE_TURNSTILE` env var controls whether Turnstile widget renders on contact form
- [ ] **FLAG-02**: When Turnstile is disabled, contact form submits without Turnstile token and API route skips verification

### SEO

- [ ] **SEO-01**: Landing page has proper title, description, and OG meta tags for social sharing
- [ ] **SEO-02**: Result pages at /[subdomain]/ have dynamic OG meta tags with subdomain name
- [ ] **SEO-03**: App has a proper favicon and app icons
- [ ] **SEO-04**: robots.txt and sitemap.xml are generated

### Design Assets

- [ ] **ASSET-01**: Custom favicon designed via Stitch MCP replaces default Next.js favicon
- [ ] **ASSET-02**: OG image template designed for social sharing previews

## Future Requirements

### Monitoring

- **MON-01**: Grafana dashboard for request metrics
- **MON-02**: Log aggregation with Loki/Promtail
- **MON-03**: Alerting on error rates

## Out of Scope

| Feature | Reason |
|---------|--------|
| Cloud deployment (AWS/GCP/Vercel) | Runs locally via Cloudflare tunnel |
| Kubernetes orchestration | Docker Compose sufficient for single machine |
| CI/CD pipeline | Can be added later; focus is local Docker |
| User authentication | Free and open, no login needed |
| Database | No persistent user data beyond redesign HTML files |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| (populated during roadmap creation) | | |

**Coverage:**
- v2 requirements: 17 total
- Mapped to phases: 0
- Unmapped: 17

---
*Requirements defined: 2026-03-21*
*Last updated: 2026-03-21 after initial definition*
