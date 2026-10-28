# CI/CD — GitHub → GCP VM

Production host: **http://35.255.220.44:8000**  
App path on VM: **`/opt/clinic-crm`**

## Repository

- GitHub: [Narayanan960080/clinic-crm](https://github.com/Narayanan960080/clinic-crm)
- Default branch: **`main`**
- On every push to `main`, [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) SSHs to the VM, `git pull` (hard reset to `origin/main`), rebuilds the API image, and runs `docker compose up -d`.

## One-time GitHub secrets

In the repo: **Settings → Secrets and variables → Actions**, add:

| Secret | Value |
|--------|--------|
| `GCP_HOST` | `35.255.220.44` |
| `GCP_USER` | `ubuntu` |
| `GCP_SSH_KEY` | Private key that can SSH as `ubuntu` (e.g. `~/.ssh/gcp_server_ed25519`) |

## One-time server setup

On the VM (after the repo exists on GitHub):

```bash
sudo bash /opt/clinic-crm/scripts/server-init-git.sh
```

If the directory is empty, clone instead:

```bash
sudo mv /opt/clinic-crm /opt/clinic-crm.bak 2>/dev/null || true
sudo git clone https://github.com/Narayanan960080/clinic-crm.git /opt/clinic-crm
cd /opt/clinic-crm && docker compose up -d --build
```

Preserve any local `.env` from a backup before replacing the tree.

## Manual deploy on the server

```bash
cd /opt/clinic-crm && ./scripts/deploy.sh
```

## Local workflow

```bash
git add -A
git commit -m "Describe your change"
git push origin main
```

Watch the **Actions** tab on GitHub for deploy status.
