## Deployment Guide

This guide covers hardening and deploying the Upstox trading system across common targets.

---

### 1. Hardened Linux VPS (Bare Metal)

1. **Provision**
   - Ubuntu 22.04 LTS, 2 vCPU, 4 GB RAM, SSD storage (>= 40 GB).
   - Static IP (or reserved floating IP) to avoid OAuth redirect changes.

2. **System prep**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo timedatectl set-timezone Asia/Kolkata
   sudo apt install -y python3.10-venv build-essential git ufw fail2ban
   ```

3. **Security**
   - `ufw allow OpenSSH`, default deny inbound, allow outbound.
   - Harden SSH (`/etc/ssh/sshd_config`) – disable password login, use SSH keys only.
   - Enable `fail2ban` for SSH and any exposed services.

4. **Deploy code**
   ```bash
   sudo useradd -m -s /bin/bash trader
   sudo su - trader
   git clone https://your-repo/upstox-bot.git && cd upstox-bot
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

5. **Secrets & env**
   - Store all credentials in `/etc/upstox-bot.env` with `chmod 600`.
   - Optionally use `pass`, `sops`, or HashiCorp Vault for rotation.

6. **Automation**
   - Follow `deploy/automation.md` for cron/systemd timers.
   - Ensure `logs/` and `data/` directories have correct ownership (`chown -R trader:trader`).

7. **Observability**
   - Tail `logs/bot.log`.
   - Add `journalctl -u upstox-bot -f` to tmux session for live monitoring.
   - Export metrics to external monitoring (Netdata, Grafana Agent, etc.).

---

### 2. AWS EC2 / Azure VM (Dockerized or Native)

#### Option A — Docker container

1. **Dockerfile**
   ```dockerfile
   FROM python:3.10-slim
   WORKDIR /app
   ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
   RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   CMD ["python", "-m", "algobot.main"]
   ```

2. **Build & push**
   ```bash
   docker build -t <registry>/upstox-bot:latest .
   docker push <registry>/upstox-bot:latest
   ```

3. **Secrets via environment**
   - Use AWS SSM Parameter Store / Secrets Manager or Azure Key Vault.
   - Inject at runtime: `docker run --env-file prod.env ...`.

4. **Scheduler**
   - AWS: use `systemd` inside EC2, or orchestrate via AWS EventBridge + SSM to start/stop the container.
   - Azure: use `cron`/systemd or Azure Automation Runbooks.

5. **High availability**
   - Run container under AWS ECS or Azure Container Apps with auto-restart policies.
   - Store logs in CloudWatch (AWSLogs driver) or Azure Monitor.

#### Option B — Native VM setup

1. **Provision**
   - AWS EC2 `t3.small` or Azure `B2s` (2 vCPU/4GB RAM).
   - Assign IAM Role/Managed Identity for secret retrieval if possible.

2. **Bootstrap script**
   Attach to user data / cloud-init:
   ```bash
   #cloud-config
   package_update: true
   packages:
     - python3.10-venv
     - build-essential
     - git
   runcmd:
     - cd /opt && git clone https://your-repo/upstox-bot.git
     - cd /opt/upstox-bot && python3 -m venv .venv
     - . /opt/upstox-bot/.venv/bin/activate && pip install -r requirements.txt
   ```

3. **Secrets**
   - Fetch via AWS Secrets Manager (`aws secretsmanager get-secret-value`) at boot and write to `/etc/upstox-bot.env`.

4. **Automation**
   - Reuse `deploy/automation.md` but ensure timers run in `Asia/Kolkata` (set `Environment="TZ=Asia/Kolkata"` inside systemd unit).

5. **Resilience**
   - Configure EC2 Auto Recovery (Status Checks) or Azure VM Auto-heal to restart instances on hardware failure.
   - Snapshots of `data/` nightly to S3/Azure Blob for disaster recovery.

---

### Networking & Compliance

- Run the bot in a private subnet and route outbound API calls via NAT Gateway; restrict inbound except SSH/VPN.
- Ensure compliance with Upstox/NSE co-location policies and SEBI algo guidelines (logs retention > 5 years, strategy approvals if required).
- Keep firmware/kernel patched; enable unattended upgrades where allowed.

---

### Deployment Checklist

- [ ] Environment variables configured and encrypted at rest.
- [ ] OAuth redirect URI registered and matches deployment URL/IP.
- [ ] Kill switch tested in staging (simulate -5% P&L).
- [ ] Websocket reconnect/resume tested under network drops.
- [ ] Monitoring + alerting wired to on-call channel.
- [ ] Backtest artifacts archived for audit (CAGR, MDD, Sharpe, Sortino, win rate, profit factor).

Following this playbook ensures the algorithmic trading stack remains resilient, observable, and compliant whether it runs on a single VPS or a managed cloud footprint.
