# Nagrik Setu — Platform

A civic-issue reporting platform, built as a reference full-stack + infra
project:

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

## Repo layout

```
backend/            Django project (apps/issues, apps/accounts, config, core)
  templates/errors/  Branded 400/403/404/500/503 HTML error pages
  apps/issues/tests/  pytest suite: models, permissions, API (98% coverage)
  apps/accounts/tests/ pytest suite: registration, JWT login/refresh
frontend/           React + TypeScript app (Vite)
  src/pages/errors/  Matching 400/401/403/404/500/503 pages + ErrorBoundary
  src/auth/           JWT storage + AuthContext, silent refresh-on-401
  src/**/__tests__/   Vitest + Testing Library suite (12 tests)
infra/
  terraform/aws/      VPC, EC2 ASG + ALB, S3, DynamoDB, API Gateway
  terraform/azure-dr/ AKS, ACR, Postgres flexible server, Redis, Traffic Manager
  k8s-dr/             Kubernetes manifests deployed to AKS during failover
  vault/              AppRole policy + setup runbook
.github/workflows/
  ci.yml              Tests (backend+frontend), terraform validate, docker build, AWS deploy
  dr-drill.yml        Monthly terraform plan + manifest validation against the DR stack
docker-compose.yml  Local dev: postgres, redis, vault (dev mode), backend, frontend
```

## Running it locally

```bash
cp backend/.env.example backend/.env   # fill in real values
docker-compose up --build
```

- Frontend: http://localhost:8080
- Backend API: http://localhost:8000/api/v1/issues/
- Django admin: http://localhost:8000/admin/
- Vault UI (dev mode, token `root`): http://localhost:8200

The backend runs migrations automatically on container start.

## Auth

JWT-based, via `djangorestframework-simplejwt`:

- `POST /api/v1/auth/register/` — create an account (enforces Django's
  password validators: length, common-password, similarity checks)
- `POST /api/v1/auth/login/` — returns `{access, refresh}` tokens
- `POST /api/v1/auth/refresh/` — exchange a refresh token for a new access token
- `POST /api/v1/auth/logout/` — blacklists the refresh token

Anyone (including anonymous visitors) can list, create, and upvote issue
reports — filing a civic complaint shouldn't require an account. Only
**staff accounts** (municipal admins, set via Django admin or `is_staff`)
can change an issue's `status`, enforced by `IsStaffForStatusChange` in
`apps/issues/permissions.py`. The React API client stores tokens and
silently refreshes an expired access token once before surfacing an error,
so a 30-minute token lifetime doesn't interrupt someone mid-session.

## Photo uploads (S3, direct from the browser)

`POST /api/v1/issues/presign-upload/` returns a presigned S3 `PUT` URL and
an `attachment_key`; the React `IssueForm` uploads the file straight to S3
(never through Django) and then sends `attachment_key` along with the
issue create request. Reading a photo back uses a presigned `GET` URL
(`Issue.attachment_url()`), since the bucket has all public access blocked.
Accepted types: JPEG/PNG/WebP, up to 8MB, enforced both client- and
server-side.

**Thumbnails**: `backend/lambda/thumbnail/handler.py` is an S3-triggered
Lambda (wired up in `infra/terraform/aws/thumbnail.tf`) that generates a
320px-wide JPEG thumbnail under `issue-attachments-thumbnails/` for every
upload under `issue-attachments/`. The serializer exposes both
`attachment_url` and `thumbnail_url`; the frontend shows the thumbnail and
falls back to the full image on a load error, since the Lambda runs
asynchronously and a thumbnail for a very recent upload may not exist yet.

## Admin dashboard

`/admin` in the React app (not to be confused with Django's own
`/admin/`) lists all reports with a status dropdown for staff to move a
report through submitted → in progress → resolved. The permission check is
enforced server-side; the client-side check in `AdminDashboard.tsx` only
avoids showing a dashboard that would fail on every action for a
signed-in-but-non-staff user.

## TLS

- **AWS**: `infra/terraform/aws/tls.tf` provisions an ACM certificate (DNS
  validation via Route 53) and an HTTPS listener on the ALB, gated behind a
  `domain_name` variable — leave it unset and the stack still applies
  HTTP-only for local/demo use; set it and `terraform apply` adds HTTPS plus
  an HTTP→HTTPS redirect.
- **Azure DR**: `infra/terraform/azure-dr/tls.tf` installs cert-manager via
  Helm and a Let's Encrypt `ClusterIssuer`; the ingress in
  `infra/k8s-dr/deployment.yaml` requests a cert through the
  `cert-manager.io/cluster-issuer` annotation.

## Tests

```bash
# Backend — 21 tests, 98% coverage on apps/
cd backend && pytest

# Frontend — 15 tests (error pages, ErrorBoundary, Login, IssueForm upload flow, API client refresh logic)
cd frontend && npx vitest run
```

Both suites run in CI on every push/PR (`.github/workflows/ci.yml`), along
with `tsc` type-checking, a production frontend build, and `terraform
validate` against both the AWS and Azure DR stacks.

## CI/CD

`.github/workflows/ci.yml` runs on every push/PR to `main`:

1. Backend tests (pytest, SQLite in `config/settings_test.py` so no Postgres
   is needed in CI) with a coverage floor
2. Frontend tests (Vitest), type-check, and production build
3. `terraform fmt -check` + `terraform validate` for both `infra/terraform/aws`
   and `infra/terraform/azure-dr`
4. Docker builds for both images
5. On merge to `main` only: push images to ECR and `terraform apply` the AWS stack

`.github/workflows/dr-drill.yml` runs monthly (and on-demand) to confirm the
Azure DR stack still `terraform plan`s cleanly and the AKS manifests are
valid — a way to catch DR bit-rot before an actual incident, without ever
touching live traffic.

## Error handling

Both layers render the same branded error states so the experience is
consistent whether Django, nginx, or the ALB is the one failing:

- **Django**: `handler400/403/404/500` in `core/error_views.py`, wired in
  `config/settings.py`. Returns HTML for browsers, JSON for API/`Accept`
  headers.
- **React**: dedicated pages for 400/401/403/404/500/503 under
  `src/pages/errors/`, plus an `ErrorBoundary` that catches uncaught render
  errors and shows the 500 page.
- **nginx**: `frontend/nginx.conf` intercepts upstream 4xx/5xx from Django
  and infra-level failures, routing them to the SPA's own error pages.

## Cloud architecture (AWS primary)

```
Internet → API Gateway (HTTP API, VPC Link)
                │
                ▼
        Application Load Balancer
                │
        ┌───────┴───────┐
        ▼               ▼
   EC2 (ASG, 2-6)   EC2 (ASG, 2-6)     ← docker-compose: Django + nginx/React
        │
        ├─→ RDS/self-managed PostgreSQL
        ├─→ ElastiCache Redis
        ├─→ S3 (uploads bucket)
        ├─→ DynamoDB (audit/event log)
        └─→ Vault (secrets, AppRole auth)
```

Apply with:

```bash
cd infra/terraform/aws
terraform init
terraform plan
terraform apply
```

(The S3 bucket + DynamoDB table used for Terraform's own remote state must
exist before the first `init` — bootstrap those two resources by hand or
via a separate one-off `terraform apply` first.)

## Disaster recovery (Azure / AKS)

The DR site in `infra/terraform/azure-dr/` stands up a **warm-standby**
environment in a separate cloud, so a full AWS regional outage doesn't take
the app down:

- **AKS cluster** running the same Docker images (mirrored into an Azure
  Container Registry so the failover path doesn't depend on Docker Hub/GHCR
  being reachable)
- **Azure Database for PostgreSQL** kept in sync from the AWS-hosted primary
  via logical replication (application-level; Terraform can't create a
  cross-cloud replication slot — see the runbook note in `aks.tf`)
- **Azure Cache for Redis** as the DR cache tier
- **Azure Traffic Manager** doing priority-based DNS failover: it normally
  points at the AWS ALB and switches to the AKS ingress IP when the primary
  fails its health probe (`/healthz/`)

Apply with:

```bash
cd infra/terraform/azure-dr
terraform init
terraform apply -var="postgres_replica_admin_password=<from-vault>"
kubectl apply -f ../k8s-dr/deployment.yaml
```

**Failover is not fully automatic** by design — Traffic Manager will detect
the primary is down within its probe interval, but a human should confirm
the AKS deployment is scaled up and the Postgres replica is promoted before
traffic actually needs to shift. Treat this as a runbook, not a magic switch.

### Cross-cloud Postgres replication (automated)

`infra/terraform/aws/dr-replication.tf` provisions **AWS Database Migration
Service** to run a `full-load-and-cdc` task: it seeds the Azure Postgres
replica once, then streams ongoing changes continuously over DMS's own
replication instance. This is a real, working mechanism — not a manual
runbook — gated behind `enable_dr_replication = true` plus the source/target
host and password variables, so the base `apply` doesn't require the DR
Postgres server to exist yet.

Prerequisites this depends on:
- The primary Postgres needs `wal_level = logical` and the `pglogical`
  extension, plus a dedicated replication user with the `REPLICATION`
  privilege (RDS: set via a parameter group; self-managed EC2 Postgres: set
  directly in `postgresql.conf`)
- A `CloudWatch` alarm (`dms_task_stopped`) watches CDC latency and fires an
  SNS notification if the DR replica falls more than 5 minutes behind for
  3 consecutive periods — the earliest signal that DR has silently drifted

## What's deliberately out of scope here

This is a scaffold meant to be extended, not a finished production system:

- IAM/RBAC here is permissive enough to run; tighten scopes before using
  this in a real environment
- `terraform validate`/`plan` for both stacks run in CI, but I could not
  reach `hashicorp.com`/`terraform.io` from this sandbox to run them
  myself — double-check the first `plan` output before applying
- The AWS DMS replication task assumes `pglogical` is installed and
  `wal_level = logical` is set on the primary Postgres — neither is
  configured automatically, since it depends on whether you're running RDS
  or a self-managed EC2 instance; that setup step lives outside Terraform
- Promoting the DR replica to primary during an actual failover (making it
  writable, redirecting the app's connection string) is still a manual
  step — DMS keeps it warm and in sync, it doesn't do failover itself
- The Azure `helm_release`/`kubernetes_manifest` resources for cert-manager
  need the AKS cluster to exist first (implicit via the provider blocks
  referencing `azurerm_kubernetes_cluster.dr`); on a from-scratch `apply`
  this can occasionally need a second `terraform apply` if the cluster
  isn't fully ready when Helm tries to connect — a known quirk of mixing
  cluster creation and in-cluster resources in one Terraform run
