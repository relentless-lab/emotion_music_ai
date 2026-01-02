## Aliyun ECS quick deployment (Docker, beginner-friendly)

This deploys:
- **Nginx** (serves Vue frontend + reverse-proxy `/api` + `/static`)
- **FastAPI backend**
- **MySQL 8** (or you can replace with Aliyun RDS)

It does **NOT** deploy the 4090 SongGen service; you keep using it via `SONGGEN_REMOTE_URL`.

### 1) Create an ECS instance
- Ubuntu 22.04 LTS (recommended)
- Open security group inbound: **80/tcp** (and **443/tcp** if you later add HTTPS)

### 2) Install Docker
On ECS:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
docker --version
docker compose version
```

### 3) Upload code to ECS
Either `git clone` your repo or upload zip to `/opt/emotion_music_ai`.

### 4) Create deploy env
On ECS:

```bash
cd /opt/emotion_music_ai
cp deploy/aliyun/env.example deploy/aliyun/.env
nano deploy/aliyun/.env
```

Important fields:
- `VITE_API_BASE_URL`: `http://<YOUR_ECS_PUBLIC_IP>` or `https://<YOUR_DOMAIN>`
- `DATABASE_URL`: keep `@db:3306` if using compose MySQL
- `SONGGEN_REMOTE_URL`: your 4090 inference service URL
- `OPENAI_API_*`: your SiliconFlow config (optional if you disable LLM)

### 5) Start services

```bash
cd /opt/emotion_music_ai/deploy/aliyun
docker compose --env-file .env up -d --build
docker compose ps
```

### 6) Open in browser
Visit:
- `http://<YOUR_ECS_PUBLIC_IP>/`

Backend docs:
- `http://<YOUR_ECS_PUBLIC_IP>/api/docs`


