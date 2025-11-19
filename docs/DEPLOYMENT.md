# AIOps 部署指南

本文檔提供 AIOps 專案的完整部署指南，包括本地開發、測試環境和生產環境的部署步驟。

## 目錄

- [環境要求](#環境要求)
- [本地開發部署](#本地開發部署)
- [Docker 部署](#docker-部署)
- [Kubernetes 生產部署](#kubernetes-生產部署)
- [配置管理](#配置管理)
- [監控和日誌](#監控和日誌)
- [備份和災難恢復](#備份和災難恢復)

---

## 環境要求

### 最低要求
- **Python**: 3.9+
- **PostgreSQL**: 13+
- **Redis**: 6.0+
- **CPU**: 2核
- **記憶體**: 4GB
- **儲存**: 20GB

### 生產環境建議
- **Python**: 3.11
- **PostgreSQL**: 15+ (含 pgvector 擴展)
- **Redis**: 7.0+
- **CPU**: 4核+
- **記憶體**: 16GB+
- **儲存**: 100GB+ SSD

### 依賴服務
- **LLM API**: OpenAI 或 Anthropic API 密鑰
- **Kubernetes**: 1.24+ (生產環境)
- **Jaeger**: 分佈式追蹤 (可選)
- **Prometheus**: 指標監控 (可選)
- **Grafana**: 可視化 (可選)

---

## 本地開發部署

### 1. 克隆專案

```bash
git clone https://github.com/markl-a/AIOps.git
cd AIOps
```

### 2. 創建虛擬環境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
```

### 3. 安裝依賴

```bash
pip install -r requirements.txt
```

### 4. 配置環境變量

```bash
cp .env.example .env
```

編輯 `.env` 文件：

```env
# LLM 配置
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL=gpt-4-turbo-preview

# 數據庫配置
DATABASE_URL=postgresql://aiops:aiops@localhost:5432/aiops

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# API 安全
ENABLE_AUTH=true
JWT_SECRET_KEY=your_secret_key_here
ADMIN_PASSWORD=your_admin_password

# 日誌配置
LOG_LEVEL=INFO
ENABLE_METRICS=true
```

### 5. 啟動服務

#### 方式 A: 使用 Docker Compose (推薦)

```bash
docker-compose up -d
```

這會啟動：
- PostgreSQL
- Redis
- AIOps API
- AIOps Worker
- AIOps Beat
- Prometheus (可選)

#### 方式 B: 手動啟動

**啟動 PostgreSQL 和 Redis** (假設已安裝)

```bash
# 創建數據庫
createdb aiops

# 運行遷移
alembic upgrade head
```

**啟動 API 服務器**

```bash
uvicorn aiops.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**啟動 Celery Worker**

```bash
celery -A aiops.tasks.celery_app worker --loglevel=info
```

**啟動 Celery Beat**

```bash
celery -A aiops.tasks.celery_app beat --loglevel=info
```

### 6. 驗證部署

訪問 http://localhost:8000/docs 查看 API 文檔

```bash
# 健康檢查
curl http://localhost:8000/health

# 獲取 Token
curl -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=admin&password=admin"
```

---

## Docker 部署

### 1. 構建鏡像

```bash
docker build -t aiops:latest .
```

### 2. 使用 Docker Compose

```bash
# 啟動所有服務
docker-compose up -d

# 查看日誌
docker-compose logs -f

# 停止服務
docker-compose down
```

### 3. 自定義配置

編輯 `docker-compose.yml`:

```yaml
services:
  aiops-api:
    environment:
      - DEFAULT_MODEL=gpt-4-turbo-preview
      - WORKERS=4
```

---

## Kubernetes 生產部署

### 前置條件

- Kubernetes 集群 (1.24+)
- kubectl 配置完成
- Helm 3.0+ (可選)

### 1. 創建命名空間

```bash
kubectl create namespace aiops
```

### 2. 創建 Secrets

```bash
# 創建 API 密鑰 Secret
kubectl create secret generic aiops-secrets \
  --from-literal=database-url=postgresql://user:pass@postgres:5432/aiops \
  --from-literal=openai-api-key=your_openai_key \
  --from-literal=anthropic-api-key=your_anthropic_key \
  -n aiops
```

### 3. 部署 PostgreSQL 和 Redis

```bash
# 使用 Helm 部署 PostgreSQL
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install postgres bitnami/postgresql \
  --set auth.username=aiops \
  --set auth.password=aiops \
  --set auth.database=aiops \
  -n aiops

# 部署 Redis
helm install redis bitnami/redis \
  --set auth.enabled=false \
  -n aiops
```

### 4. 部署 AIOps 應用

```bash
# 應用 Kubernetes 配置
kubectl apply -f k8s/base/ -n aiops

# 查看部署狀態
kubectl get pods -n aiops
kubectl get svc -n aiops
```

### 5. 配置 Ingress

編輯 `k8s/base/ingress.yaml` 設置你的域名：

```yaml
spec:
  tls:
  - hosts:
    - your-domain.com
  rules:
  - host: your-domain.com
```

應用配置：

```bash
kubectl apply -f k8s/base/ingress.yaml -n aiops
```

### 6. 配置自動擴展

HPA 已包含在配置中，驗證：

```bash
kubectl get hpa -n aiops
```

### 7. 運行數據庫遷移

```bash
# 進入 API Pod
kubectl exec -it deployment/aiops-api -n aiops -- bash

# 運行遷移
alembic upgrade head
```

---

## 配置管理

### 環境變量

所有配置通過環境變量管理：

| 變量名 | 描述 | 默認值 |
|--------|------|--------|
| `DATABASE_URL` | PostgreSQL 連接字符串 | - |
| `REDIS_URL` | Redis 連接字符串 | - |
| `OPENAI_API_KEY` | OpenAI API 密鑰 | - |
| `ANTHROPIC_API_KEY` | Anthropic API 密鑰 | - |
| `DEFAULT_LLM_PROVIDER` | 默認 LLM 提供商 | `openai` |
| `DEFAULT_MODEL` | 默認模型 | `gpt-4-turbo-preview` |
| `LOG_LEVEL` | 日誌級別 | `INFO` |
| `ENABLE_AUTH` | 啟用認證 | `true` |
| `JWT_SECRET_KEY` | JWT 密鑰 | - |
| `ENABLE_METRICS` | 啟用監控 | `true` |
| `OTLP_ENDPOINT` | OpenTelemetry 端點 | - |

### ConfigMap 配置

```bash
kubectl create configmap aiops-config \
  --from-literal=log-level=INFO \
  --from-literal=default-model=gpt-4-turbo-preview \
  -n aiops
```

---

## 監控和日誌

### Prometheus 指標

AIOps 暴露以下 Prometheus 指標：

- `/metrics` - 應用指標端點

主要指標：
- `aiops_http_requests_total` - HTTP 請求總數
- `aiops_agent_executions_total` - 代理執行總數
- `aiops_llm_requests_total` - LLM 請求總數
- `aiops_llm_cost_total` - LLM 總成本
- `aiops_errors_total` - 錯誤總數

### 部署 Prometheus

```bash
kubectl apply -f monitoring/prometheus/
```

### Grafana 儀表板

1. 部署 Grafana:
```bash
helm install grafana bitnami/grafana -n aiops
```

2. 導入儀表板:
- 訪問 Grafana UI
- 導入 `monitoring/grafana/dashboards/*.json`

### 日誌聚合

日誌以 JSON 格式輸出到 `logs/` 目錄。

**使用 ELK/EFK Stack**:

```bash
# 安裝 Filebeat
kubectl apply -f monitoring/logging/filebeat.yaml -n aiops
```

**查看日誌**:

```bash
# 實時查看 API 日誌
kubectl logs -f deployment/aiops-api -n aiops

# 查看 Worker 日誌
kubectl logs -f deployment/aiops-worker -n aiops
```

---

## 備份和災難恢復

### 數據庫備份

**手動備份**:

```bash
# 備份數據庫
pg_dump -h localhost -U aiops aiops > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢復數據庫
psql -h localhost -U aiops aiops < backup_20240101_120000.sql
```

**自動備份 (Kubernetes CronJob)**:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 2 * * *"  # 每天凌晨 2 點
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15
            command:
            - /bin/sh
            - -c
            - pg_dump -h postgres -U aiops aiops | gzip > /backup/db_$(date +\%Y\%m\%d).sql.gz
```

### 災難恢復計劃

詳見 [DISASTER_RECOVERY.md](./DISASTER_RECOVERY.md)

---

## 故障排查

### 常見問題

**1. API 無法連接數據庫**

```bash
# 檢查數據庫連接
kubectl exec deployment/aiops-api -n aiops -- \
  psql $DATABASE_URL -c "SELECT 1"
```

**2. Worker 無法處理任務**

```bash
# 檢查 Redis 連接
kubectl exec deployment/aiops-worker -n aiops -- \
  redis-cli -u $REDIS_URL ping
```

**3. 高記憶體使用**

```bash
# 查看資源使用
kubectl top pods -n aiops
```

詳細故障排查請參考 [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

---

## 安全最佳實踐

1. ✅ 使用強密碼和密鑰
2. ✅ 啟用 TLS/SSL 加密
3. ✅ 定期更新依賴
4. ✅ 使用 Kubernetes Secrets 管理敏感數據
5. ✅ 啟用 Pod Security Policies
6. ✅ 定期備份數據
7. ✅ 啟用審計日誌
8. ✅ 限制 API 速率

---

## 性能調優

### API 服務器

```yaml
# 增加 worker 數量
command: ["uvicorn", "aiops.api.main:app", "--workers", "4"]

# 調整資源限制
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

### Worker 並發

```yaml
# Celery worker 並發設置
args:
  - "--concurrency=8"
  - "--max-tasks-per-child=100"
```

### 數據庫連接池

```python
# 調整連接池大小
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
)
```

---

## 擴展性考慮

- **水平擴展**: 使用 HPA 自動擴展 Pod
- **垂直擴展**: 增加 Pod 資源限制
- **數據庫**: 使用 PostgreSQL 讀寫分離
- **緩存**: 使用 Redis Cluster
- **負載均衡**: 使用 Ingress Controller

---

## 相關文檔

- [故障排查指南](./TROUBLESHOOTING.md)
- [災難恢復計劃](./DISASTER_RECOVERY.md)
- [最佳實踐](./BEST_PRACTICES.md)
- [API 文檔](./API.md)

---

**更新日期**: 2024-01-15
**版本**: 1.0.0
