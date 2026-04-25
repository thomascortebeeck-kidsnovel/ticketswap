# Setup wizard (`web/`)

A small FastAPI app that renders a form, validates it server-side, and
returns a `ticketswap-config.zip` containing `.env`, `watches.json`, and
an `INSTALL.txt` for the user.

The bot itself **does not run here**. Each end-user still runs the bot
locally on their own machine - this site only generates the config and
the install instructions. That keeps the wizard inside Cloud Run free
tier and avoids the (substantial) ToS / liability problems of running
TicketSwap automations centrally. See `PLAN.md` for the full reasoning.

## What this app does NOT do

- Save anything to disk or a database. Inputs flow form → validation → zip
  → response, then are dropped.
- Log form bodies. Cloud Run's default request log captures method, path,
  status - not bodies.
- Send WhatsApp / email itself. The user's apikey + Gmail App Password
  are written into the zip and never used by this server.

## Run it locally

From the repo root:

```bash
pip install -e ".[web]"
uvicorn web.app:app --reload --port 8080
```

Then open http://localhost:8080.

To require a password on the form, set `ACCESS_PASSWORD`:

```bash
ACCESS_PASSWORD=letmein uvicorn web.app:app --reload --port 8080
```

## Deploy to Cloud Run (free tier)

One-time setup:

```bash
# Replace with your project + region. eu-west1 (Belgium) is closest for
# Belgian / NL users. us-central1 / us-east1 / us-west1 are also fine.
PROJECT_ID=your-gcp-project
REGION=europe-west1

gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

Deploy from source (Cloud Build builds the container, pushes to Artifact
Registry, deploys to Cloud Run, all in one command):

```bash
gcloud run deploy ticketswap-helper \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory 256Mi \
  --max-instances 5 \
  --port 8080
```

The first deploy takes a few minutes (Cloud Build downloading base
images). Subsequent deploys are faster.

To restrict access to people with a shared password:

```bash
gcloud run deploy ticketswap-helper \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars ACCESS_PASSWORD=some-shared-secret
```

## Free-tier sanity check

Cloud Run free tier per month:
- 2,000,000 requests
- 360,000 vCPU-seconds
- 180,000 GiB-seconds
- 1 GiB egress to North America

The wizard is stateless, scales to zero, and each request is a few KB. A
personal-scale deployment will cost **$0/month** until usage is large
enough that you almost certainly want to monetise it anyway.

Cloud Build also has a free quota (120 build-minutes/day). Each `gcloud
run deploy --source .` uses 1-2 minutes.

## Custom domain (optional)

Cloud Run can map a custom domain you own:

```bash
gcloud beta run domain-mappings create \
  --service ticketswap-helper \
  --domain helper.yourdomain.com \
  --region "$REGION"
```

Follow the DNS instructions it prints. HTTPS certificate is auto-managed.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8080` | Set automatically by Cloud Run. |
| `ACCESS_PASSWORD` | unset | If set, the form requires this password. |
| `GITHUB_REPO` | `thomascortebeeck-kidsnovel/ticketswap` | Used in install instructions to point users at the right repo. |
| `GIT_BRANCH` | `main` | Used in install instructions for the README link. |
