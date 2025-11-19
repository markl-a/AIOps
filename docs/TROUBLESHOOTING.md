# AIOps 故障排查手冊

本文檔提供 AIOps 專案常見問題的診斷和解決方法。

## 目錄

- [快速診斷](#快速診斷)
- [API 相關問題](#api-相關問題)
- [數據庫問題](#數據庫問題)
- [LLM 相關問題](#llm-相關問題)
- [Celery Worker 問題](#celery-worker-問題)
- [性能問題](#性能問題)
- [Kubernetes 問題](#kubernetes-問題)
- [監控和日誌](#監控和日誌)

---

## 快速診斷

### 系統健康檢查

```bash
# 檢查 API 健康狀態
curl http://localhost:8000/health

# 檢查就緒狀態
curl http://localhost:8000/ready

# 查看指標
curl http://localhost:8000/metrics
```

### Kubernetes 快速診斷

```bash
# 查看所有 Pod 狀態
kubectl get pods -n aiops

# 查看 Pod 日誌
kubectl logs -f deployment/aiops-api -n aiops

# 查看 Pod 資源使用
kubectl top pods -n aiops

# 查看 Events
kubectl get events -n aiops --sort-by='.lastTimestamp'
```

---

## API 相關問題

### 問題 1: API 無法啟動

**症狀**:
```
Error: Could not connect to database
```

**診斷**:
```bash
# 檢查數據庫連接
psql $DATABASE_URL -c "SELECT 1"

# 檢查環境變量
env | grep DATABASE_URL
```

**解決方案**:
1. 確認數據庫服務已啟動
2. 檢查連接字符串格式: `postgresql://user:pass@host:port/dbname`
3. 驗證網絡連通性: `telnet db-host 5432`
4. 檢查防火牆規則

### 問題 2: 401 Unauthorized

**症狀**:
```json
{"detail": "Could not validate credentials"}
```

**診斷**:
```bash
# 測試 Token 生成
curl -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=admin&password=admin"
```

**解決方案**:
1. 確認 JWT_SECRET_KEY 已設置
2. 檢查用戶名和密碼
3. 確認 Token 格式: `Bearer <token>`
4. 檢查 Token 是否過期（默認 60 分鐘）

### 問題 3: 429 Too Many Requests

**症狀**:
```json
{"detail": "Rate limit exceeded"}
```

**診斷**:
```bash
# 檢查 Redis 連接
redis-cli -u $REDIS_URL ping

# 查看當前速率限制
curl http://localhost:8000/api/v1/rate-limit-status
```

**解決方案**:
1. 減慢請求頻率
2. 增加速率限制: 設置 `RATE_LIMIT=200`
3. 使用不同的 API Key
4. 檢查 Redis 是否正常運行

### 問題 4: 500 Internal Server Error

**診斷步驟**:

```bash
# 1. 查看詳細日誌
tail -f logs/aiops_$(date +%Y-%m-%d).log

# 2. 查看錯誤日誌
tail -f logs/aiops_errors_$(date +%Y-%m-%d).log

# 3. 查看 Sentry（如已配置）
# 訪問 Sentry 控制台查看詳細堆棧
```

**常見原因**:
- LLM API 密鑰無效
- 數據庫連接丟失
- 內存不足
- 依賴服務不可用

---

## 數據庫問題

### 問題 1: 連接池耗盡

**症狀**:
```
QueuePool limit of size 10 overflow 20 reached
```

**診斷**:
```bash
# 查看活動連接數
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity WHERE datname='aiops';"

# 查看長時間運行的查詢
psql $DATABASE_URL -c "
SELECT pid, now() - query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;
"
```

**解決方案**:
1. 增加連接池大小:
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,  # 默認 10
    max_overflow=40,  # 默認 20
)
```

2. 終止長時間運行的查詢:
```sql
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'active' AND now() - query_start > interval '5 minutes';
```

3. 添加連接超時:
```python
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)
```

### 問題 2: 慢查詢

**診斷**:
```sql
-- 啟用慢查詢日誌
ALTER DATABASE aiops SET log_min_duration_statement = 1000;  -- 1秒

-- 查看最慢的查詢
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

**解決方案**:
1. 添加索引
2. 優化查詢
3. 使用 EXPLAIN ANALYZE 分析執行計劃

### 問題 3: 數據庫磁盤空間不足

**診斷**:
```sql
-- 查看表大小
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**解決方案**:
1. 清理舊數據（見維護任務）
2. 啟用自動 VACUUM
3. 增加磁盤空間

---

## LLM 相關問題

### 問題 1: OpenAI Rate Limit

**症狀**:
```
Error: Rate limit exceeded
```

**診斷**:
```bash
# 查看 Token 使用情況
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/usage

# 查看應用內成本追蹤
curl http://localhost:8000/api/v1/costs/summary
```

**解決方案**:
1. 啟用自動重試:
```python
from aiops.core.error_handler import retry_on_error

@retry_on_error(max_retries=3, backoff_factor=2.0)
async def call_llm():
    ...
```

2. 實現速率限制:
```python
# 在代理執行前添加延遲
import asyncio
await asyncio.sleep(1.0)  # 1秒延遲
```

3. 切換到其他模型或提供商:
```env
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_MODEL=claude-3-sonnet-20240229
```

### 問題 2: LLM 響應超時

**症狀**:
```
Error: Request timed out after 30s
```

**解決方案**:
1. 增加超時時間:
```python
from openai import AsyncOpenAI
client = AsyncOpenAI(timeout=60.0)  # 60秒
```

2. 減少輸入長度
3. 使用更快的模型

### 問題 3: 無效的 API 密鑰

**診斷**:
```bash
# 測試 OpenAI 密鑰
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 測試 Anthropic 密鑰
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01"
```

**解決方案**:
1. 驗證 API 密鑰有效性
2. 檢查環境變量設置
3. 確認 API 配額未用盡

---

## Celery Worker 問題

### 問題 1: Worker 無法連接到 Broker

**症狀**:
```
Error: Cannot connect to redis://localhost:6379/0
```

**診斷**:
```bash
# 測試 Redis 連接
redis-cli -u $REDIS_URL ping

# 檢查 Redis 日誌
docker logs redis
```

**解決方案**:
1. 確認 Redis 服務運行中
2. 檢查 CELERY_BROKER_URL 配置
3. 驗證網絡連通性
4. 檢查 Redis 認證配置

### 問題 2: 任務一直處於 PENDING 狀態

**診斷**:
```bash
# 檢查 Worker 狀態
celery -A aiops.tasks.celery_app inspect active

# 檢查隊列長度
redis-cli -u $REDIS_URL llen celery

# 查看 Worker 日誌
kubectl logs deployment/aiops-worker -n aiops
```

**解決方案**:
1. 確認 Worker 已啟動
2. 檢查任務路由配置
3. 增加 Worker 並發數:
```bash
celery -A aiops.tasks.celery_app worker --concurrency=8
```

### 問題 3: 任務執行失敗

**診斷**:
```python
# 查看任務結果
from celery.result import AsyncResult
result = AsyncResult(task_id)
print(result.status)
print(result.traceback)
```

**解決方案**:
1. 查看錯誤追蹤
2. 檢查任務參數
3. 驗證依賴服務可用性
4. 查看 Worker 資源使用

---

## 性能問題

### 問題 1: API 響應慢

**診斷**:
```bash
# 測試端點響應時間
time curl http://localhost:8000/api/v1/agents/code-review

# 查看 Prometheus 指標
curl http://localhost:8000/metrics | grep http_request_duration
```

**優化建議**:
1. 啟用響應緩存
2. 增加 Worker 數量
3. 優化數據庫查詢
4. 使用 CDN
5. 啟用 Gzip 壓縮

### 問題 2: 高內存使用

**診斷**:
```bash
# 查看進程內存使用
ps aux | grep uvicorn

# Kubernetes 環境
kubectl top pods -n aiops
```

**解決方案**:
1. 增加內存限制:
```yaml
resources:
  limits:
    memory: "2Gi"
```

2. 減少 Worker 並發數
3. 啟用內存分析:
```python
import tracemalloc
tracemalloc.start()
```

### 問題 3: CPU 使用率高

**診斷**:
```bash
# 查看 CPU 使用
top -p $(pgrep -f uvicorn)

# 性能分析
python -m cProfile -o profile.stats aiops/api/main.py
```

**解決方案**:
1. 水平擴展（增加 Pod 副本）
2. 優化計算密集型代碼
3. 使用異步處理
4. 啟用 CPU 親和性

---

## Kubernetes 問題

### 問題 1: Pod CrashLoopBackOff

**診斷**:
```bash
# 查看 Pod 狀態
kubectl describe pod <pod-name> -n aiops

# 查看 Pod 日誌
kubectl logs <pod-name> -n aiops --previous
```

**常見原因**:
1. 應用啟動失敗
2. 配置錯誤
3. 健康檢查失敗
4. 資源不足

**解決方案**:
```bash
# 修改健康檢查
kubectl edit deployment/aiops-api -n aiops

# 增加初始延遲
initialDelaySeconds: 60
```

### 問題 2: ImagePullBackOff

**診斷**:
```bash
# 查看詳細信息
kubectl describe pod <pod-name> -n aiops
```

**解決方案**:
1. 確認鏡像名稱正確
2. 檢查鏡像倉庫訪問權限
3. 配置 imagePullSecrets:
```bash
kubectl create secret docker-registry regcred \
  --docker-server=<registry> \
  --docker-username=<username> \
  --docker-password=<password>
```

### 問題 3: HPA 不工作

**診斷**:
```bash
# 查看 HPA 狀態
kubectl get hpa -n aiops
kubectl describe hpa aiops-api-hpa -n aiops

# 檢查 metrics-server
kubectl get deployment metrics-server -n kube-system
```

**解決方案**:
1. 安裝 metrics-server
2. 確認資源請求已設置
3. 檢查 CPU/內存指標可用性

---

## 監控和日誌

### 啟用詳細日誌

```bash
# 設置日誌級別為 DEBUG
export LOG_LEVEL=DEBUG

# Kubernetes
kubectl set env deployment/aiops-api LOG_LEVEL=DEBUG -n aiops
```

### 查看結構化日誌

```bash
# 解析 JSON 日誌
tail -f logs/aiops_$(date +%Y-%m-%d).log | jq '.'

# 過濾特定 trace_id
tail -f logs/aiops_$(date +%Y-%m-%d).log | jq 'select(.trace_id=="xxx")'
```

### 使用分佈式追蹤

```bash
# 查看 Jaeger UI
kubectl port-forward svc/jaeger-query 16686:16686 -n aiops

# 訪問 http://localhost:16686
```

---

## 緊急恢復程序

### 數據庫恢復

```bash
# 1. 停止所有連接
psql $DATABASE_URL -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'aiops' AND pid <> pg_backend_pid();
"

# 2. 從備份恢復
psql $DATABASE_URL < backup_latest.sql

# 3. 驗證數據
psql $DATABASE_URL -c "SELECT count(*) FROM users;"
```

### 回滾部署

```bash
# Kubernetes 回滾
kubectl rollout undo deployment/aiops-api -n aiops

# 查看回滾狀態
kubectl rollout status deployment/aiops-api -n aiops
```

### 清除 Redis 緩存

```bash
# 清除所有緩存
redis-cli -u $REDIS_URL FLUSHDB

# 清除特定 Key
redis-cli -u $REDIS_URL DEL "cache:*"
```

---

## 獲取幫助

如果問題仍未解決：

1. **查看日誌**: `logs/aiops_errors_*.log`
2. **查看 Sentry**: 檢查錯誤追蹤
3. **查看 Metrics**: Prometheus/Grafana
4. **提交 Issue**: https://github.com/markl-a/AIOps/issues

---

**更新日期**: 2024-01-15
**版本**: 1.0.0
