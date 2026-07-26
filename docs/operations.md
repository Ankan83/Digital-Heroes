# Observability & Rollback Plan

## 1. Metrics to Monitor

### 1.1 Business Metrics (Customer-Facing)

| Metric | Instrument | Source | Target |
|--------|-----------|--------|--------|
| `audit_latency_p99` | Histogram | API middleware | < 2s |
| `audit_latency_p95` | Histogram | API middleware | < 1s |
| `audit_error_rate` | Counter | Audit service | < 1% |
| `audit_throughput` | Counter | API middleware | 10K/day |
| `cache_hit_rate` | Gauge | Cache wrapper | > 80% |
| `customer_sla_violations` | Counter | SLA tracker | 0 |

### 1.2 Infrastructure Metrics

| Metric | Instrument | Source | Alert Threshold |
|--------|-----------|--------|-----------------|
| `api_cpu_utilization` | Gauge | ECS | > 70% |
| `api_memory_utilization` | Gauge | ECS | > 80% |
| `worker_pool_utilization` | Gauge | Worker semaphore | > 90% |
| `queue_depth` | Gauge | RabbitMQ | > 1,000 |
| `queue_consumer_lag` | Gauge | RabbitMQ | > 30s |
| `redis_memory_used` | Gauge | Redis INFO | > 80% |
| `redis_evicted_keys` | Counter | Redis INFO | > 100/min |
| `db_connections_active` | Gauge | PostgreSQL | > 80% of max |
| `db_slow_queries` | Counter | PostgreSQL pg_stat | > 10/min |

### 1.3 External Dependency Metrics

| Metric | Instrument | Source | Alert Threshold |
|--------|-----------|--------|-----------------|
| `external_timeout_rate` | Counter | Audit client | > 5% |
| `external_dns_failures` | Counter | Validator | > 1% |
| `external_avg_response_time` | Histogram | Audit client | > 3s |

---

## 2. Dashboard Design

### 2.1 Grafana Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│  URL Audit Service — Production Overview                    │
├─────────────────────────────────────────────────────────────┤
│  [SLA Status: 🟢 HEALTHY]  [Cache Hit: 87%]  [QPS: 12]   │
├──────────────────────┬──────────────────────────────────────┤
│  Latency (p50/p99)   │  Error Rate (%)                      │
│  ┌────────────────┐  │  ┌────────────────────────────────┐  │
│  │    /\        │  │  │     ▁▂▄▆█                      │  │
│  │   /  \  ____  │  │  │    ▁▄▆████▄▂                   │  │
│  │  /    \/    \ │  │  │   ▂▄███████▄▂                  │  │
│  │ /      \     \│  │  │  ▁▄██████████▄▁                │  │
│  └────────────────┘  │  └────────────────────────────────┘  │
├──────────────────────┼──────────────────────────────────────┤
│  Queue Depth         │  Worker Pool Usage                   │
│  ┌────────────────┐  │  ┌────────────────────────────────┐  │
│  │ ▁▂▄▆▇████▆▄▂▁ │  │  │  ████████████████████░░░░░░░░  │  │
│  │                │  │  │  78% active (39/50 workers)    │  │
│  └────────────────┘  │  └────────────────────────────────┘  │
├──────────────────────┼──────────────────────────────────────┤
│  Top 10 URLs Audited │  Error Breakdown                     │
│  ┌────────────────┐  │  ┌────────────────────────────────┐  │
│  │ 1. google.com  │  │  │  TIMEOUT    ████████████ 45% │  │
│  │ 2. github.com  │  │  │  DNS_FAIL   ██████       22% │  │
│  │ 3. amazon.com  │  │  │  403        ████         18% │  │
│  └────────────────┘  │  │  500        ██           10% │  │
│                      │  └────────────────────────────────┘  │
└──────────────────────┴──────────────────────────────────────┘
```

### 2.2 Key Dashboards

| Dashboard | URL | Refresh | Audience |
|-----------|-----|---------|----------|
| Executive Summary | `/d/executive` | 5m | Leadership |
| Engineering Overview | `/d/engineering` | 10s | SRE Team |
| API Performance | `/d/api-perf` | 10s | Backend Team |
| Queue Health | `/d/queue` | 5s | Platform Team |
| Cost Analysis | `/d/cost` | 1h | Finance |

---

## 3. Alerting Strategy

### 3.1 Alert Severity Definitions

| Severity | Response Time | Notification Channel | Escalation |
|----------|--------------|---------------------|------------|
| **P1 (Critical)** | 5 minutes | PagerDuty + Slack #incidents | Auto-page on-call engineer |
| **P2 (High)** | 30 minutes | Slack #alerts + Email | Page if unacknowledged in 30m |
| **P3 (Warning)** | 4 hours | Slack #alerts-only | No page, dashboard only |

### 3.2 Alert Rules

```yaml
# P1 Alerts (Page immediately)
- alert: AuditLatencyP99Critical
  expr: histogram_quantile(0.99, rate(audit_latency_bucket[5m])) > 2
  for: 2m
  severity: p1

- alert: AuditErrorRateCritical
  expr: rate(audit_errors_total[5m]) / rate(audit_total[5m]) > 0.01
  for: 2m
  severity: p1

- alert: ServiceDown
  expr: up{job="audit-api"} == 0
  for: 1m
  severity: p1

- alert: QueueDepthCritical
  expr: rabbitmq_queue_messages{queue=~"audit.*"} > 5000
  for: 2m
  severity: p1

# P2 Alerts (Notify, page if unacknowledged)
- alert: CacheHitRateLow
  expr: cache_hit_rate < 0.8
  for: 5m
  severity: p2

- alert: WorkerPoolNearExhaustion
  expr: worker_pool_utilization > 0.9
  for: 3m
  severity: p2

- alert: RedisMemoryHigh
  expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.8
  for: 5m
  severity: p2

- alert: DBConnectionsHigh
  expr: pg_stat_activity_count / pg_settings_max_connections > 0.8
  for: 5m
  severity: p2

# P3 Alerts (Dashboard only)
- alert: ExternalTimeoutElevated
  expr: rate(external_timeout_total[5m]) / rate(audit_total[5m]) > 0.05
  for: 10m
  severity: p3

- alert: CacheEvictionRateHigh
  expr: rate(redis_evicted_keys_total[5m]) > 100
  for: 10m
  severity: p3
```

### 3.3 Alert Routing

```
PagerDuty ──▶ On-call Engineer (P1)
     │
     └──▶ Escalation Manager (if unacknowledged 15m)

Slack #incidents ──▶ All engineers (P1 + P2)
Slack #alerts ──▶ SRE team (P2 + P3)
Email ──▶ Team leads (weekly digest)
```

---

## 4. Logging Strategy

### 4.1 Log Levels

| Level | Use Case | Retention | Example |
|-------|----------|-----------|---------|
| **ERROR** | Failures requiring investigation | 90 days | `Audit failed: timeout` |
| **WARN** | Anomalies, retries | 30 days | `Cache miss rate elevated` |
| **INFO** | Normal operations | 14 days | `Audit completed: 200ms` |
| **DEBUG** | Development/troubleshooting | 7 days | `HTTP headers: {...}` |

### 4.2 Structured Log Format (JSON)

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "service": "audit-api",
  "version": "1.0.0",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "abc123def456",
  "span_id": "span789",
  "message": "Audit completed",
  "fields": {
    "url": "https://example.com",
    "status_code": 200,
    "response_time_ms": 245,
    "cached": false,
    "client_ip": "203.0.113.42",
    "user_agent": "Mozilla/5.0..."
  }
}
```

### 4.3 Log Aggregation

| Environment | Tool | Query Language |
|-------------|------|---------------|
| Development | Local file + `jq` | JSONPath |
| Staging | CloudWatch Logs | CloudWatch Insights |
| Production | Datadog / Splunk | SPL / DQL |

---

## 5. Distributed Tracing

### 5.1 Trace Structure

```
Trace: abc123def456
├── Span: api-request (0ms - 250ms)
│   ├── Span: rate-limit-check (0ms - 1ms)
│   ├── Span: cache-lookup (1ms - 3ms) [MISS]
│   ├── Span: queue-publish (3ms - 15ms)
│   ├── Span: worker-process (15ms - 245ms)
│   │   ├── Span: http-request (20ms - 220ms)
│   │   │   ├── Span: dns-lookup (20ms - 25ms)
│   │   │   ├── Span: tcp-connect (25ms - 30ms)
│   │   │   ├── Span: tls-handshake (30ms - 45ms)
│   │   │   └── Span: http-transfer (45ms - 220ms)
│   │   ├── Span: response-parse (220ms - 240ms)
│   │   └── Span: cache-write (240ms - 245ms)
│   └── Span: db-write (245ms - 250ms)
```

### 5.2 Trace Sampling

| Environment | Sampling Rate | Storage |
|-------------|--------------|---------|
| Development | 100% | Jaeger (local) |
| Staging | 100% | AWS X-Ray |
| Production | 1% (error traces: 100%) | AWS X-Ray + S3 archive |

---

## 6. Rollback Strategy

### 6.1 Blue/Green Deployment

```
┌──────────────┐
│  Route 53    │── Weighted routing ──▶┌──────────┐ (100%)
│  (DNS)       │                       │  Blue    │  v1.0.0 (stable)
└──────────────┘                       └──────────┘
         │
         └─────────────────────────────▶┌──────────┐ (0%)
                                      │  Green   │  v1.1.0 (new)
                                      └──────────┘
```

**Deployment Steps:**
1. Deploy v1.1.0 to Green environment
2. Run smoke tests against Green
3. Shift 10% traffic to Green
4. Monitor error rate for 5 minutes
5. If error rate < 0.5%, shift to 50%
6. If stable for 10 minutes, shift to 100%
7. Keep Blue running for 1 hour as hot standby

**Rollback Trigger Conditions:**
- Error rate > 0.5% for 2 minutes
- Latency p99 > 3s for 3 minutes
- Any P1 alert fires during rollout
- Manual trigger by on-call engineer

**Rollback Procedure (5 minutes):**
```bash
# 1. Identify current active color
ACTIVE_COLOR=$(aws route53 get-health-check-status --id $HC_ID | jq -r '.Status')

# 2. Switch DNS to stable color
aws route53 change-resource-record-sets   --hosted-zone-id $ZONE_ID   --change-batch file://rollback-to-blue.json

# 3. Scale new color to 0
aws ecs update-service   --cluster prod   --service audit-api-green   --desired-count 0

# 4. Verify via health checks
curl https://api.urlaudit.com/health

# 5. Post-mortem
# Create incident in #incidents Slack channel
```

### 6.2 Database Migration Rollback

**Policy: Expand-Only Migrations**

| Phase | Action | Rollback Safety |
|-------|--------|-----------------|
| **Expand** | Add new columns/tables (nullable) | Old code ignores new columns |
| **Migrate** | Deploy new code that uses new schema | New code works with old schema |
| **Contract** | Remove old columns (next release) | Only after 100% adoption |

**Rollback Commands:**
```sql
-- If migration caused issues:
-- 1. Revert application code (blue/green DNS flip)
-- 2. New columns are ignored by old code — no DB action needed
-- 3. If data corruption occurred, restore from RDS snapshot

-- Restore from snapshot (last resort)
aws rds restore-db-instance-to-point-in-time   --source-db-instance-identifier audit-db   --target-db-instance-identifier audit-db-rollback   --restore-time 2024-01-15T10:00:00Z
```

### 6.3 Feature Flags

Use **LaunchDarkly** (or open-source **Unleash**) for instant feature toggles:

```python
# In application code
if ld_client.variation("ssl-check-enabled", user, True):
    ssl_info = extract_ssl_info(response)
else:
    ssl_info = None
```

**Emergency Toggle Examples:**
- `ssl-check-enabled`: Disable if SSL checking causes CPU spike
- `cache-warming-enabled`: Disable if warming causes queue overload
- `new-rate-limiter`: Revert to old rate limiter if new one has bugs

**Toggle Procedure:**
```bash
# Disable feature instantly (no redeployment)
curl -X PATCH https://app.launchdarkly.com/api/v2/flags/default/ssl-check-enabled   -H "Authorization: $LD_API_KEY"   -d '{"patch":[{"op":"replace","path":"/environments/production/on","value":false}]}'
```

### 6.4 Runbook: Complete Rollback Checklist

```
┌─────────────────────────────────────────────────────────────┐
│  EMERGENCY ROLLBACK RUNBOOK                                 │
├─────────────────────────────────────────────────────────────┤
│  Step 1: Identify the problem                               │
│    □ Check #incidents Slack for context                     │
│    □ Check Grafana for error rate / latency spikes          │
│    □ Check CloudWatch Logs for stack traces                 │
│                                                             │
│  Step 2: Execute rollback (choose one)                      │
│    □ Blue/Green: Flip Route 53 to stable color              │
│    □ Feature Flag: Disable problematic feature in LaunchDarkly│
│    □ DB: Restore from RDS snapshot (last resort)            │
│                                                             │
│  Step 3: Verify rollback                                    │
│    □ Health check: curl /api/v1/health                      │
│    □ Smoke test: Run postman collection                     │
│    □ Monitor: Watch error rate for 10 minutes               │
│                                                             │
│  Step 4: Communicate                                        │
│    □ Update #incidents with status                          │
│    □ Notify customers if SLA was breached                   │
│    □ Schedule post-mortem within 24 hours                   │
│                                                             │
│  Step 5: Post-mortem                                        │
│    □ Document root cause in wiki                            │
│    □ Create Jira ticket for permanent fix                   │
│    □ Update runbook if procedure was unclear                │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. SLOs & SLIs

### 7.1 Service Level Objectives

| SLO | Target | Measurement Window | Burn Rate Alert |
|-----|--------|-------------------|-----------------|
| Availability | 99.9% | 30 days | > 0.1% error budget/day |
| Latency p99 | < 2s | 7 days | > 2.5s for 1 hour |
| Cache Hit Rate | > 80% | 1 day | < 75% for 30 minutes |
| Error Rate | < 0.1% | 1 day | > 0.5% for 10 minutes |

### 7.2 Error Budget

```
Monthly error budget: 0.1% × 30 days = 43.2 minutes downtime

Burn rate alerts:
- 1x burn: 43.2 min/month → Normal operations
- 2x burn: 21.6 min/month → Investigate during business hours
- 10x burn: 4.3 min/month → Page on-call immediately
- 100x burn: 26 min total → Stop all deployments immediately
```

---

## 8. Tooling Stack

| Function | Tool | Alternative |
|----------|------|-------------|
| Metrics | Prometheus + Grafana | Datadog, New Relic |
| Logs | CloudWatch Logs + Grafana Loki | Splunk, ELK |
| Traces | AWS X-Ray | Jaeger, Zipkin |
| Alerts | PagerDuty + Slack | Opsgenie, VictorOps |
| Feature Flags | LaunchDarkly | Unleash, Flagsmith |
| APM | Datadog APM | New Relic, Dynatrace |
| Synthetic Monitoring | Pingdom | UptimeRobot, Grafana Synthetic |
