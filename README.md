# Nagrik Setu — Platform

| Layer | Choice |
|---|---|
| Frontend | React 18 + TypeScript (Vite), served by nginx |
| Backend | Django 5 + Django REST Framework, JWT auth (SimpleJWT) |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Secrets | HashiCorp Vault (AppRole auth) |
| Containers | Docker, docker-compose (local) |
| IaC | Terraform |
| CI/CD | GitHub Actions — tests, terraform validate, docker build, deploy |
| Cloud (primary) | AWS — EC2 (ASG behind an ALB), S3, DynamoDB, API Gateway |
| Cloud (disaster recovery) | Azure — AKS, Azure Database for PostgreSQL, Azure Cache for Redis, Traffic Manager |

## About the application

**Nagrik Setu** ("citizen bridge") is a civic-issue reporting platform: a
direct channel between residents and the municipal staff responsible for
fixing everyday urban problems — potholes, water outages, uncollected
garbage, power cuts, broken streetlights, transport complaints, pollution,
and grievances/corruption reports.

**How it works, end to end:**

1. A resident (no account required) opens the app, picks a category and
   locality, describes the problem, and optionally attaches a photo. The
   photo uploads directly to S3 from the browser via a presigned URL — the
   report is created the moment they submit, with a short, shareable
   tracking ID (`NS-XXXXXX`).
2. Other residents who see the same problem can find the existing report
   and **upvote** it instead of filing a duplicate, so the loudest signal
   municipal staff see is genuine community impact, not noise.
3. An AI triage step reads the free-text description, double-checks it
   against the category the citizen picked, and estimates urgency —
   surfacing the reports that matter most sooner, without asking the
   citizen to fill in more fields.
4. Municipal staff work from an admin dashboard, moving each report through
   **submitted → in progress → resolved**. Every status change and every
   upvote is written to an append-only audit trail, so there's a durable
   record of what happened and when.
5. The resident can check back on their tracking ID at any time to see
   whether their report has been picked up.

**Why it helps end users:**

- **Zero friction to report.** No sign-up wall for the single most
  important action in the app — filing a complaint. Accounts exist only
  for the staff side that needs accountability (who changed a status).
- **Collective visibility instead of a black hole.** A pothole reported by
  40 people shows 40 upvotes on one tracking ID, not 40 identical
  complaints nobody can prioritize. Citizens can see it's been seen.
- **A receipt, not a shout into the void.** The tracking ID and status
  turn "I complained once and heard nothing" into something the citizen
  can actually follow up on.
- **Works even when a photo won't upload cleanly.** Everything degrades
  gracefully — a report is still valid without a photo, and a slow or
  failed thumbnail never blocks the report itself from being visible.

**How this differs from typical municipal complaint systems / other apps
in this space:**

- Most government complaint portals require an account, a long form, and
  give no visibility into whether anyone else reported the same thing.
  Nagrik Setu is anonymous-first and upvote-driven, so duplicate reports
  become a *prioritization signal* instead of duplicate paperwork for
  staff to wade through.
- Generic "citizen engagement" SaaS products are usually category-agnostic
  and not built around a specific civic taxonomy; Nagrik Setu's categories
  (roads, water, garbage, power, lighting, transport, pollution,
  grievances) map directly onto how Indian municipal departments are
  actually organized, so a report can be routed correctly from day one.
- It's built with an AI triage layer from the ground up (see Architecture)
  rather than bolted on — a report's *urgency* and *correct category* are
  inferred automatically, rather than relying entirely on the citizen or
  a human reviewer to get it right.
- It's designed to survive a full cloud outage: most civic-tech projects
  at this scale have no disaster-recovery story at all; this one runs a
  warm-standby copy of the whole stack in a second cloud (see Disaster
  recovery below), because a civic complaint system going dark during an
  actual emergency (a storm knocking out power *and* the app that reports
  power outages) defeats its own purpose.

## Architecture

```
                              ┌─────────────────────────┐
                              │        Citizen /         │
                              │      Municipal Staff      │
                              └────────────┬─────────────┘
                                           │ HTTPS
                                           ▼
                              ┌─────────────────────────┐
                              │  API Gateway (VPC Link)  │
                              └────────────┬─────────────┘
                                           ▼
                              ┌─────────────────────────┐
                              │  Application Load        │
                              │  Balancer (ACM/TLS)       │
                              └────────────┬─────────────┘
                                           ▼
                        ┌──────────────────┴──────────────────┐
                        ▼                                      ▼
              ┌───────────────────┐                  ┌───────────────────┐
              │  EC2 (ASG 2–6)     │   ...            │  EC2 (ASG 2–6)     │
              │  nginx → React SPA │                  │  nginx → React SPA │
              │  Django + DRF API  │                  │  Django + DRF API  │
              └─────────┬──────────┘                  └─────────┬──────────┘
                        │                                        │
        ┌───────────────┼────────────────┬───────────────┬───────┴────────┐
        ▼               ▼                ▼               ▼                ▼
  PostgreSQL 16     Redis 7          S3 (uploads)    DynamoDB        HashiCorp Vault
  (issues, users)   (cache,          (issue photos)  (audit/event   (secrets, via
                     sessions,                        log)           AppRole auth)
                     upvote-dedupe,
                     rate limits)
                        │
                        ▼
              ┌───────────────────────────────┐
              │   S3 event-triggered Lambdas    │
              │  • thumbnail generator          │
              │  • upload-validation (real       │
              │    file-type check, EXIF/GPS     │
              │    stripping, quarantine)        │
              └───────────────────────────────┘

              ┌───────────────────────────────┐
              │   AI triage agent (async)        │
              │   category/urgency suggestion,    │
              │   feature-flagged, best-effort    │
              └───────────────────────────────┘
```

**Request flow for a new report:**
`React IssueForm → presigned S3 PUT (photo, if any) → POST /api/v1/issues/
→ Postgres write → Redis stats-cache invalidation → DynamoDB audit event →
AI triage (async, best-effort) →` response with the tracking ID back to
the citizen. In parallel, the S3 upload (if present) fans out to the
thumbnail Lambda and the upload-validation Lambda, both triggered off the
same `s3:ObjectCreated` event.

**Layers, and why each exists:**

- **Frontend (React + nginx):** a single-page app so status checks and
  upvotes feel instant; nginx also serves branded error pages if the API
  is unreachable, so a backend outage doesn't show a blank page.
- **Backend (Django + DRF + SimpleJWT):** anonymous-friendly permissions
  by default (`IsAuthenticatedOrReadOnly`), with a narrow, explicit
  exception (`IsStaffForStatusChange`) for the one action that needs
  accountability — changing a report's status.
- **PostgreSQL:** source of truth for issues and accounts.
- **Redis:** short-TTL cache for the dashboard's stats endpoint, session
  backend, and the abuse-control state (upvote dedupe keys, throttle
  counters) — all things that should be fast and don't need to survive a
  cache flush.
- **S3 + Lambdas:** photos never transit Django; a presigned URL lets the
  browser upload directly, and two independent, single-purpose Lambdas
  react to that event — one for thumbnails, one for validating the upload
  actually is what it claims to be before it's ever served publicly.
- **DynamoDB:** an append-only mirror of every state-changing event, so
  ward-level activity dashboards can query recent activity without adding
  load to Postgres.
- **Vault:** the only place real secrets live; the app authenticates via
  AppRole and falls back to `.env` only in local dev.
- **Terraform (AWS + Azure DR):** the AWS stack is the primary; the Azure
  stack is a warm standby kept in sync via DMS logical replication and
  fronted by Traffic Manager for failover — see `infra/terraform/azure-dr`
  and `infra/terraform/aws/dr-replication.tf`.
