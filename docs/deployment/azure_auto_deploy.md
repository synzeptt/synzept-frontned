# Azure VM Automatic Deployment

This runbook configures Synzept so every push to `main` validates the app and deploys the backend to the Azure VM automatically.

## Workflow

GitHub Actions workflow:

- `.github/workflows/deploy-production.yml`

Trigger:

- `push` to `main`
- manual `workflow_dispatch`

Pipeline:

1. Install frontend dependencies.
2. Run frontend linting, type checking, and production build.
3. Install backend dependencies.
4. Run backend/API tests.
5. SSH to the Azure VM.
6. Fetch and reset the production checkout to the pushed commit.
7. Activate the backend virtual environment.
8. Install backend dependencies.
9. Run `python -m alembic upgrade head`.
10. Restart the Synzept systemd service.
11. Verify the backend health endpoint.

Deployment stops if tests, migrations, service restart, or health checks fail.

## Required GitHub Secrets

Set these in GitHub:

`Settings -> Secrets and variables -> Actions -> New repository secret`

| Secret | Example | Purpose |
|---|---|---|
| `AZURE_VM_HOST` | `20.244.28.232` | Public IP or DNS name for the Azure VM. |
| `AZURE_VM_PORT` | `22` | SSH port. Use `22` unless the VM uses a custom port. |
| `AZURE_VM_USER` | `deploy` | Linux user used by GitHub Actions. |
| `AZURE_VM_SSH_KEY` | private key contents | Private SSH key for the deploy user. |
| `BACKEND_DEPLOY_PATH` | `/opt/synzept` | Absolute path to the repo checkout on the VM. |
| `BACKEND_SERVICE_NAME` | `synzept` | systemd service name to restart. |
| `BACKEND_HEALTH_URL` | `https://api.synzept.com/health/ready` | Public backend readiness endpoint. |

Do not store production `.env` values in GitHub Actions unless the deployment is changed to generate env files. The current workflow expects production environment files to already exist on the VM.

## Azure VM Setup

Run once on the Azure VM as an administrator.

### 1. Create Deploy User

```bash
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG www-data deploy
sudo mkdir -p /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chown -R deploy:deploy /home/deploy/.ssh
```

Create an SSH key locally or in a secure admin machine:

```bash
ssh-keygen -t ed25519 -C "github-actions-synzept-deploy" -f synzept_deploy
```

Add the public key to the VM:

```bash
sudo tee -a /home/deploy/.ssh/authorized_keys < synzept_deploy.pub
sudo chmod 600 /home/deploy/.ssh/authorized_keys
sudo chown deploy:deploy /home/deploy/.ssh/authorized_keys
```

Add the private key contents from `synzept_deploy` to GitHub as `AZURE_VM_SSH_KEY`.

### 2. Prepare Production Checkout

Choose the production path. The workflow examples use `/opt/synzept`.

```bash
sudo mkdir -p /opt/synzept
sudo chown deploy:deploy /opt/synzept
sudo -u deploy git clone https://github.com/synzeptt/synzept-frontned.git /opt/synzept
cd /opt/synzept
sudo -u deploy git checkout main
```

If the repo is private, configure the deploy user's GitHub access with a deploy key or machine-user token before cloning.

### 3. Prepare Backend Environment

```bash
cd /opt/synzept/backend
sudo -u deploy python3.12 -m venv .venv
sudo -u deploy .venv/bin/python -m pip install --upgrade pip
sudo -u deploy .venv/bin/python -m pip install -r requirements.txt
```

Create the production backend environment file on the VM:

```bash
sudo -u deploy nano /opt/synzept/backend/.env
```

Confirm it contains production values for database, auth, CORS, AI provider, billing, and Google/Razorpay settings.

### 4. Configure systemd

Create `/etc/systemd/system/synzept.service`:

```ini
[Unit]
Description=Synzept Backend
After=network.target

[Service]
User=deploy
Group=www-data
WorkingDirectory=/opt/synzept/backend
EnvironmentFile=/opt/synzept/backend/.env
ExecStart=/opt/synzept/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable synzept
sudo systemctl start synzept
sudo systemctl status synzept --no-pager
```

### 5. Allow Limited Restart Access

GitHub Actions needs to restart only the Synzept service.

Create `/etc/sudoers.d/synzept-deploy`:

```sudoers
deploy ALL=(root) NOPASSWD: /bin/systemctl restart synzept, /bin/journalctl -u synzept -n 120 --no-pager
```

Validate:

```bash
sudo visudo -cf /etc/sudoers.d/synzept-deploy
```

If the service name is different, update both the sudoers file and `BACKEND_SERVICE_NAME`.

## Deployment Verification

After pushing to `main`:

1. Open GitHub Actions.
2. Confirm `Deploy Production` completed successfully.
3. Confirm the summary shows the expected commit.
4. Verify backend:

```bash
curl --fail https://api.synzept.com/health/ready
curl --fail https://api.synzept.com/health
```

5. Verify new authenticated routes exist. Without a token, protected routes should return `401`, not `404`:

```bash
curl -i https://api.synzept.com/api/v2/agent-memory/timeline
curl -i https://api.synzept.com/api/v2/autonomous-workspace
```

6. Verify frontend routes:

```bash
curl -I https://app.synzept.com/dashboard
curl -I https://app.synzept.com/daily-brief
curl -I https://app.synzept.com/open-loops
curl -I https://app.synzept.com/agent
curl -I https://app.synzept.com/billing
```

7. Sign in through `https://app.synzept.com/login` and verify Dashboard, Daily Brief, Open Loops, AI chat, Billing, and Razorpay flows.

## Rollback

Rollback requires a deliberate operator decision because database migrations may not be safely reversible.

### Backend Code Rollback

On the VM:

```bash
cd /opt/synzept
git fetch origin main
git log --oneline -n 10
git reset --hard <known-good-commit>
cd backend
. .venv/bin/activate
python -m pip install -r requirements.txt
sudo systemctl restart synzept
curl --fail https://api.synzept.com/health/ready
```

### Migration Rollback

Only downgrade migrations when the migration file is known to be reversible and data loss has been considered.

```bash
cd /opt/synzept/backend
. .venv/bin/activate
python -m alembic current
python -m alembic downgrade -1
sudo systemctl restart synzept
curl --fail https://api.synzept.com/health/ready
```

If migrations are not safely reversible, keep the migrated database and roll forward with a corrective commit.

## Failure Handling

The workflow fails fast:

- frontend lint/type/build failure stops deployment
- backend test failure stops deployment
- `alembic upgrade head` failure stops deployment before restart
- systemd restart failure stops deployment
- health check failure stops deployment and prints the latest service logs

The GitHub Actions `production` environment can be configured with required reviewers if deployment approval is desired later.
