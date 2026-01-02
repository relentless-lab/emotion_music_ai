## Aliyun ECS quick deployment (Docker, beginner-friendly)

This deploys:
- **Nginx** (serves Vue frontend + reverse-proxy `/api` + `/static`)
- **FastAPI backend**
- **MySQL 8** (optional; you can also use Aliyun RDS)

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
docker-compose --version || true
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
- `DATABASE_URL`:
  - If using compose MySQL: keep `@db:3306`
  - If using **Aliyun RDS**: set `@rm-xxx.rds.aliyuncs.com:3306/...` (recommend adding `?charset=utf8mb4`)
- `SONGGEN_REMOTE_URL`: your 4090 inference service URL
- `OPENAI_API_*`: your SiliconFlow config (optional if you disable LLM)

### 5) Start services

#### Option A: Use local MySQL (compose)

```bash
cd /opt/emotion_music_ai/deploy/aliyun
docker-compose --env-file .env up -d --build
docker-compose ps
```

#### Option B: Use Aliyun RDS (no local MySQL)
This avoids pulling/running the `mysql:8.0` image.

```bash
cd /opt/emotion_music_ai/deploy/aliyun
docker-compose --env-file .env up -d --build --scale db=0
docker-compose ps
```

### 6) Open in browser
Visit:
- `http://<YOUR_ECS_PUBLIC_IP>/`

Backend docs:
- `http://<YOUR_ECS_PUBLIC_IP>/api/docs`

### If Docker Hub pull times out (common)
Configure registry mirrors and restart docker:

```bash
sudo mkdir -p /etc/docker
cat | sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn",
    "https://registry.docker-cn.com"
  ]
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker
docker info | grep -i mirror -A 5 || true
```


