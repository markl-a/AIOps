# AIOps 最佳實踐指南

本文檔提供 AIOps 專案的最佳實踐和使用建議，幫助你充分發揮系統能力並避免常見陷阱。

## 目錄

- [架構設計](#架構設計)
- [安全最佳實踐](#安全最佳實踐)
- [性能優化](#性能優化)
- [成本控制](#成本控制)
- [開發流程](#開發流程)
- [運維管理](#運維管理)
- [監控和告警](#監控和告警)

---

## 架構設計

### 1. 微服務分離

✅ **推薦做法**:
```yaml
# 分離 API 和 Worker
services:
  aiops-api:
    # 處理 HTTP 請求
  aiops-worker:
    # 處理異步任務
  aiops-beat:
    # 定時任務調度
```

❌ **避免**:
- 在 API 進程中執行長時間運行的任務
- 混合同步和異步處理邏輯

### 2. 無狀態設計

✅ **推薦做法**:
```python
# 使用外部狀態存儲
from aiops.database import get_db

def process_request(request_id):
    # 從數據庫讀取狀態
    db = next(get_db())
    state = db.query(State).filter_by(id=request_id).first()
```

❌ **避免**:
- 在內存中存儲用戶會話
- 依賴本地文件系統

### 3. 優雅降級

✅ **推薦做法**:
```python
from aiops.core.exceptions import LLMProviderError

try:
    result = await agent.execute(code=code)
except LLMProviderError:
    # 降級到簡單規則引擎
    result = fallback_analysis(code)
```

---

## 安全最佳實踐

### 1. API 密鑰管理

✅ **推薦做法**:
```bash
# 使用 Kubernetes Secrets
kubectl create secret generic aiops-secrets \
  --from-literal=openai-api-key=$OPENAI_KEY

# 使用環境變量
export OPENAI_API_KEY=$(cat /run/secrets/openai-key)
```

❌ **避免**:
- 在代碼中硬編碼 API 密鑰
- 將密鑰提交到 Git
- 在日誌中打印密鑰

### 2. 最小權限原則

✅ **推薦做法**:
```yaml
# Pod Security Context
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
```

### 3. 輸入驗證

✅ **推薦做法**:
```python
from pydantic import BaseModel, validator

class CodeReviewRequest(BaseModel):
    code: str
    language: str

    @validator('code')
    def validate_code(cls, v):
        if len(v) > 100000:  # 100KB
            raise ValueError('Code too large')
        return v
```

### 4. 速率限制

✅ **推薦做法**:
```python
# 多層速率限制
# 1. API 級別
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

# 2. 用戶級別
@app.get("/analyze")
@limiter.limit("10/minute")
async def analyze():
    ...

# 3. LLM 級別
await asyncio.sleep(1.0)  # 避免過快調用
```

### 5. 數據加密

✅ **推薦做法**:
- 傳輸加密: 啟用 TLS/SSL
- 靜態加密: 加密數據庫備份
- 密鑰輪換: 定期更換 API 密鑰

---

## 性能優化

### 1. 緩存策略

✅ **推薦做法**:
```python
from aiops.core.cache import cache

@cache(ttl=3600)  # 緩存 1 小時
async def get_code_analysis(code_hash):
    # 昂貴的 LLM 調用
    return await llm.analyze(code)
```

**緩存層次**:
1. **應用層緩存** (Redis): 用於 LLM 響應
2. **數據庫緩存** (查詢緩存): 用於頻繁查詢
3. **CDN 緩存**: 用於靜態資源

### 2. 批量處理

✅ **推薦做法**:
```python
# 批量處理文件
from celery import group

tasks = [
    code_review_task.s(file)
    for file in files
]
job = group(tasks)
result = job.apply_async()
```

### 3. 連接池管理

✅ **推薦做法**:
```python
# 數據庫連接池
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Redis 連接池
redis_pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50,
)
```

### 4. 異步處理

✅ **推薦做法**:
```python
# 使用異步 I/O
import asyncio

async def process_multiple_files(files):
    tasks = [analyze_file(f) for f in files]
    results = await asyncio.gather(*tasks)
    return results
```

### 5. 資源限制

✅ **推薦做法**:
```yaml
# Kubernetes 資源限制
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

---

## 成本控制

### 1. Token 預算管理

✅ **推薦做法**:
```python
from aiops.core.config import Config

config = Config(
    max_tokens_per_request=4000,
    daily_token_budget=1000000,
    monthly_cost_limit=500.0,  # USD
)
```

### 2. 模型選擇策略

✅ **推薦做法**:
```python
# 根據任務複雜度選擇模型
def select_model(task_complexity):
    if task_complexity == "simple":
        return "gpt-3.5-turbo"  # 便宜快速
    elif task_complexity == "medium":
        return "gpt-4-turbo-preview"
    else:
        return "claude-3-opus"  # 最強但貴
```

### 3. 成本監控

✅ **推薦做法**:
```python
# 啟用成本追蹤
from aiops.observability.metrics import llm_cost_total

# 設置成本告警
if daily_cost > budget_limit:
    send_alert("Daily LLM budget exceeded")
```

### 4. 緩存復用

✅ **推薦做法**:
```python
# 對相同代碼的分析結果復用
code_hash = hashlib.sha256(code.encode()).hexdigest()
cached_result = cache.get(f"analysis:{code_hash}")
if cached_result:
    return cached_result
```

---

## 開發流程

### 1. 代碼審查檢查清單

在提交代碼前檢查：

- [ ] 是否添加了單元測試
- [ ] 是否更新了文檔
- [ ] 是否處理了錯誤情況
- [ ] 是否添加了日誌記錄
- [ ] 是否進行了安全審查
- [ ] 是否考慮了性能影響
- [ ] 是否符合代碼風格

### 2. Git 分支策略

✅ **推薦做法**:
```bash
# 功能分支
git checkout -b feature/new-agent
git push origin feature/new-agent

# PR 合並前確保
- 所有測試通過
- CI/CD 檢查通過
- Code Review 完成
```

### 3. 版本管理

✅ **推薦做法**:
- 使用語義化版本 (Semantic Versioning)
- 維護 CHANGELOG.md
- 對重大更改提供遷移指南

### 4. 測試策略

✅ **推薦做法**:
```python
# 測試金字塔
# 70% - 單元測試
def test_agent_validation():
    agent = CodeReviewAgent()
    with pytest.raises(ValidationError):
        agent.execute(code="")

# 20% - 集成測試
def test_api_workflow():
    response = client.post("/api/v1/code-review", ...)
    assert response.status_code == 200

# 10% - E2E 測試
def test_complete_analysis_pipeline():
    # 測試完整流程
```

---

## 運維管理

### 1. 部署策略

✅ **推薦做法**:

**滾動更新**:
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

**金絲雀部署**:
```bash
# 首先部署 10% 流量
kubectl set image deployment/aiops-api api=aiops:v2.0 -n aiops
kubectl scale deployment/aiops-api-canary --replicas=1 -n aiops

# 監控指標，如果正常則全量部署
```

### 2. 數據庫遷移

✅ **推薦做法**:
```bash
# 1. 備份數據庫
pg_dump -h localhost -U aiops aiops > backup.sql

# 2. 運行遷移（在維護窗口）
alembic upgrade head

# 3. 驗證遷移
alembic current

# 4. 如有問題，回滾
alembic downgrade -1
```

### 3. 日誌管理

✅ **推薦做法**:
```python
# 結構化日誌
from aiops.core.structured_logger import get_structured_logger

log = get_structured_logger(__name__)
log.info(
    "Agent execution started",
    agent_name="code_reviewer",
    user_id=user_id,
    trace_id=trace_id,
)
```

**日誌保留策略**:
- ERROR 日誌: 90 天
- INFO 日誌: 30 天
- DEBUG 日誌: 7 天

### 4. 備份策略

✅ **推薦做法**:

**3-2-1 原則**:
- 3 個備份副本
- 2 種不同介質
- 1 個異地備份

```yaml
# Kubernetes CronJob
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-backup
spec:
  schedule: "0 2 * * *"  # 每天凌晨 2 點
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15
            command: ["/backup.sh"]
```

---

## 監控和告警

### 1. 關鍵指標監控

✅ **推薦監控**:

**服務健康**:
- API 可用性 (>99.9%)
- 響應時間 (P95 < 1s)
- 錯誤率 (< 0.1%)

**資源使用**:
- CPU 使用率 (< 70%)
- 內存使用率 (< 80%)
- 磁盤使用率 (< 80%)

**業務指標**:
- LLM 調用次數
- LLM 成本
- 活躍用戶數
- 任務隊列長度

### 2. 告警規則

✅ **推薦告警**:

```yaml
# Prometheus 告警規則
groups:
  - name: aiops_alerts
    rules:
      # API 錯誤率過高
      - alert: HighErrorRate
        expr: rate(aiops_errors_total[5m]) > 0.01
        for: 5m
        annotations:
          summary: "High error rate detected"

      # LLM 成本超標
      - alert: HighLLMCost
        expr: aiops_llm_cost_total > 500
        annotations:
          summary: "Daily LLM cost exceeded $500"

      # 數據庫連接池耗盡
      - alert: DBConnectionPoolExhausted
        expr: aiops_db_connections_active >= aiops_db_connections_total
        for: 2m
```

### 3. SLO/SLA 定義

✅ **推薦 SLO**:

| 指標 | 目標 |
|------|------|
| API 可用性 | 99.9% |
| API 響應時間 (P95) | < 1s |
| API 響應時間 (P99) | < 3s |
| 數據持久性 | 99.999% |
| 任務處理時間 | 95% 在 5 分鐘內 |

---

## 常見陷阱

### ❌ 避免的做法

1. **不要在循環中調用 LLM**
```python
# ❌ 錯誤
for file in files:
    await llm.analyze(file)  # 很慢很貴

# ✅ 正確
await batch_analyze(files)  # 使用批量處理
```

2. **不要忽略錯誤**
```python
# ❌ 錯誤
try:
    result = await agent.execute()
except:
    pass  # 靜默失敗

# ✅ 正確
try:
    result = await agent.execute()
except AgentError as e:
    log.error(f"Agent failed: {e}")
    return fallback_result
```

3. **不要阻塞事件循環**
```python
# ❌ 錯誤
def sync_heavy_work():
    time.sleep(10)  # 阻塞

# ✅ 正確
async def async_heavy_work():
    await asyncio.sleep(10)  # 非阻塞
```

4. **不要過度緩存**
```python
# ❌ 錯誤
@cache(ttl=86400 * 365)  # 緩存 1 年
async def get_security_scan():
    ...  # 安全掃描結果應該經常更新

# ✅ 正確
@cache(ttl=3600)  # 緩存 1 小時
```

---

## 檢查清單

### 生產部署檢查清單

在生產環境部署前確保：

#### 安全
- [ ] 所有密鑰使用 Secrets 管理
- [ ] 啟用 TLS/SSL
- [ ] 配置防火牆規則
- [ ] 啟用速率限制
- [ ] 配置 CORS 白名單

#### 可靠性
- [ ] 配置健康檢查
- [ ] 配置就緒檢查
- [ ] 設置資源限制
- [ ] 配置自動擴展 (HPA)
- [ ] 設置備份策略

#### 監控
- [ ] 配置 Prometheus 指標
- [ ] 設置 Grafana 儀表板
- [ ] 配置告警規則
- [ ] 啟用分佈式追蹤
- [ ] 配置日誌聚合

#### 性能
- [ ] 啟用緩存
- [ ] 優化數據庫索引
- [ ] 配置連接池
- [ ] 啟用 CDN
- [ ] 壓縮響應

#### 數據
- [ ] 運行數據庫遷移
- [ ] 驗證數據完整性
- [ ] 測試備份恢復
- [ ] 配置數據保留策略

---

## 相關資源

- [部署指南](./DEPLOYMENT.md)
- [故障排查](./TROUBLESHOOTING.md)
- [API 文檔](./API.md)
- [架構文檔](../ARCHITECTURE.md)

---

**更新日期**: 2024-01-15
**版本**: 1.0.0
