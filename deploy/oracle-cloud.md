# Oracle Cloud Always Free 배포 가이드

`ASF-Orchestrator` 중간 서버를 Oracle Cloud **Always Free** VM에 배포하는 절차입니다.

## 왜 Oracle Cloud Always Free 인가

- **상시 무료**: Ampere A1 (ARM) 최대 4 OCPU / 24GB RAM, 또는 AMD 1/8 OCPU x2
- 블록 스토리지 200GB, 아웃바운드 10TB/월
- 상시 켜져 있어 **스케줄 수집**에 적합 (서버리스의 cold start 없음)

> 대안: Google Cloud Run(서버리스, 저트래픽 무료), Fly.io, Render(무료는 유휴 시 슬립).

## 1. VM 생성

1. Oracle Cloud 콘솔 → Compute → Instances → **Create instance**
2. Image: **Ubuntu 22.04**, Shape: **VM.Standard.A1.Flex** (ARM, 1~4 OCPU / 6~24GB)
   - A1 용량 부족 시 **VM.Standard.E2.1.Micro**(AMD, Always Free)로 대체
3. SSH 공개키 등록 후 생성

## 2. 방화벽/보안 목록

- VCN → Security List → Ingress Rule 추가: TCP **8000** (또는 80/443)
- VM 내부 방화벽:
  ```bash
  sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT
  sudo netfilter-persistent save   # 또는 ufw allow 8000
  ```

## 3. 앱 설치

```bash
sudo apt update && sudo apt install -y python3-venv git
sudo mkdir -p /opt/asf-orchestrator && sudo chown $USER /opt/asf-orchestrator
git clone https://github.com/oksk1111/ASF-Orchestrator.git /opt/asf-orchestrator
cd /opt/asf-orchestrator
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
nano .env       # ADMIN_PASSWORD, MAFRA_API_KEY, KAMIS_SERVICE_KEY 설정
```

## 4. systemd 서비스 등록

```bash
sudo cp deploy/asf-orchestrator.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now asf-orchestrator
sudo systemctl status asf-orchestrator
```

- 소비자 API: `http://<VM_PUBLIC_IP>:8000/api/v1/...`
- 관리자 웹: `http://<VM_PUBLIC_IP>:8000/admin`

## 5. (권장) HTTPS 리버스 프록시 — Caddy

```bash
sudo apt install -y caddy
echo 'your-domain.com {
    reverse_proxy localhost:8000
}' | sudo tee /etc/caddy/Caddyfile
sudo systemctl restart caddy
```

도메인이 있으면 Caddy가 Let's Encrypt 인증서를 자동 발급합니다.

## 6. Docker 대안

```bash
docker build -t asf-orchestrator .
docker run -d --name asf-orch -p 8000:8000 --env-file .env \
  -v $PWD/data:/app/data --restart unless-stopped asf-orchestrator
```

## 7. fresh_alert 연동

`fresh_alert` 백엔드의 `ASF_ORCHESTRATOR_BASE_URL`을 이 서버 주소로 설정:

```
ASF_ORCHESTRATOR_BASE_URL=http://<VM_PUBLIC_IP>:8000
```
