# Failure Mode Analysis

## Overview

This document identifies the three most likely failure scenarios for the scaled URL Audit Service and defines mitigation strategies for each.

---

## Failure 1: Queue Overload (Backpressure)

### Scenario
A traffic spike or batch job overwhelms RabbitMQ. Queue depth grows beyond worker capacity. Messages accumulate faster than they can be processed.

### Impact Assessment

| Impact | Severity | Description |
|--------|----------|-------------|
| SLA Breach | **Critical** | Response times exceed 2s p99 guarantee |
| Memory Exhaustion | **High** | RabbitMQ nodes run out of RAM, crash |
| Cascading Failure | **High** | Workers crash, reducing capacity further |
| Customer Churn | **Medium** | VIP customers experience degraded service |

### Root Causes
1. Sudden viral traffic (e.g., product launch, Hacker News front page)
2. Batch audit job submitted without rate limiting
3. Worker pool scaled down unexpectedly
4. Slow external websites causing worker thread blocking

### Detection

```yaml
# Prometheus alert
alert: QueueDepthHigh
expr: rabbitmq_queue_messages{queue="audit.normal"} > 5000
for: 2m
labels:
  severity: p1
annotations:
  summary: "Queue depth exceeds 5000 messages"
  runbook_url: "https://wiki.internal/runbooks/queue-overload"
```

### Mitigation Strategy

#### Immediate (0-5 minutes)
1. **Auto-scale workers**: CloudWatch alarm triggers ECS worker scaling (5 → 30 tasks)
2. **Circuit breaker**: API Gateway returns `503 Service Unavailable` with `Retry-After: 30` when queue depth > 5,000
3. **Shed non-critical traffic**: Drop `audit.bulk` queue messages first

#### Short-term (5-30 minutes)
1. **Priority escalation**: Move VIP customers to dedicated `audit.priority` queue
2. **Rate limit batch jobs**: Throttle API keys submitting >100 req/min
3. **Increase worker concurrency**: Temporarily raise `MAX_CONCURRENCY` from 100 → 200

#### Long-term (post-incident)
1. **Implement predictive scaling**: Scale workers 5 minutes before predicted peak (based on historical patterns)
2. **Queue sharding**: Partition by URL hash to parallelize processing
3. **Add queue depth to health check**: Return `429` from `/health` when overloaded

### Recovery Verification
```bash
# Check queue depth
rabbitmqctl list_queues name messages

# Verify worker scaling
aws ecs describe-services --cluster prod --services audit-workers

# Test SLA compliance
k6 run --vus 100 --duration 5m load-test.js
```

---

## Failure 2: Cache Failure (Redis Outage)

### Scenario
Redis cluster experiences a split-brain, node failure, or network partition. Cache reads fail or return stale data.

### Impact Assessment

| Impact | Severity | Description |
|--------|----------|-------------|
| Latency Spike | **Critical** | All requests hit external websites directly (10x latency) |
| External Site Overload | **High** | We become a DDoS source for popular URLs |
| SLA Breach | **Critical** | p99 latency jumps from 50ms to 5s+ |
| Worker Exhaustion | **Medium** | Workers blocked on slow external requests |

### Root Causes
1. Redis primary node failure (hardware failure)
2. Network partition between Redis nodes
3. Memory exhaustion (keys not expiring properly)
4. ElastiCache maintenance window during peak hours

### Detection

```yaml
# Prometheus alert
alert: RedisUnavailable
expr: up{job="redis"} == 0
for: 1m
labels:
  severity: p1

alert: CacheHitRateLow
expr: (rate(redis_keyspace_hits[5m]) / (rate(redis_keyspace_hits[5m]) + rate(redis_keyspace_misses[5m]))) < 0.8
for: 5m
labels:
  severity: p2
```

### Mitigation Strategy

#### Immediate (0-2 minutes)
1. **Local LRU fallback**: Each API node maintains 1-minute in-memory cache (Caffeine/go-cache) for hot URLs
2. **Redis Sentinel failover**: Automatic promotion of replica to primary (< 10s downtime)
3. **Graceful degradation**: 
   - Increase HTTP client timeout from 5s → 8s
   - Reduce max concurrency from 100 → 50 to prevent worker exhaustion

#### Short-term (2-15 minutes)
1. **Cache warming**: Background worker pre-populates cache for top 1,000 URLs
2. **Read from replica**: Route cache reads to healthy replicas during primary recovery
3. **Alert on-call**: If failover doesn't resolve within 5 minutes

#### Long-term (post-incident)
1. **Redis Cluster mode**: Migrate from single-primary to cluster mode (6+ nodes)
2. **Cross-AZ replication**: Ensure replicas are in different availability zones
3. **Cache pre-warming on startup**: New nodes fetch hot keys before joining the pool

### Recovery Verification
```bash
# Check Redis health
redis-cli -h prod-cache.abc123.cache.amazonaws.com ping

# Verify cache hit rate
curl -s http://localhost:9090/metrics | grep cache_hit_rate

# Test latency
wrk -t4 -c100 -d30s http://localhost:8080/api/v1/audit
```

---

## Failure 3: External Website Timeout / Slowloris

### Scenario
Target websites are down, slow, or under attack. Workers spend excessive time waiting for HTTP responses, causing queue buildup and worker pool exhaustion.

### Impact Assessment

| Impact | Severity | Description |
|--------|----------|-------------|
| Worker Pool Exhaustion | **Critical** | All workers blocked, no capacity for new jobs |
| Queue Buildup | **High** | Normal audits delayed behind slow ones |
| SLA Breach | **Critical** | Even fast websites can't be audited |
| Resource Waste | **Medium** | CPU/memory consumed by idle connections |

### Root Causes
1. Target website under DDoS attack
2. Target website server misconfiguration (Slowloris)
3. Network partition between our workers and target
4. Large file downloads (e.g., 100MB PDF served as HTML)

### Detection

```yaml
# Prometheus alert
alert: ExternalTimeoutRateHigh
expr: rate(audit_external_timeout_total[5m]) / rate(audit_total[5m]) > 0.05
for: 3m
labels:
  severity: p2

alert: WorkerPoolExhausted
expr: audit_worker_active / audit_worker_total > 0.95
for: 2m
labels:
  severity: p1
```

### Mitigation Strategy

#### Immediate (0-1 minute)
1. **Aggressive timeouts**: 5s connect, 8s total response (configurable per client tier)
2. **Connection pooling**: Reuse TCP connections to reduce handshake overhead
3. **Circuit breaker per domain**: If >50% of requests to `example.com` timeout in 1 minute, block that domain for 5 minutes

#### Short-term (1-10 minutes)
1. **Async with webhook**: For slow sites, return `202 Accepted` immediately; callback when complete
2. **Separate thread pools**: Isolated goroutine pools for external I/O vs internal processing
3. **Domain blacklist**: Auto-block domains with >90% timeout rate over 1 hour
4. **Response size limit**: Abort if response body exceeds 10MB

#### Long-term (post-incident)
1. **Adaptive timeouts**: Machine learning model predicts optimal timeout per domain based on historical data
2. **Geographic worker distribution**: Workers in EU/US/Asia to minimize latency to local websites
3. **HTTP/2 prioritization**: Use HTTP/2 multiplexing to avoid head-of-line blocking

### Recovery Verification
```bash
# Check worker pool status
curl http://localhost:8080/metrics | grep worker_pool

# Test specific domain
curl -X POST http://localhost:8080/api/v1/audit   -d '{"url": "https://slow-site.com"}'

# Verify circuit breaker state
curl http://localhost:8080/metrics | grep circuit_breaker
```

---

## Failure Summary Matrix

| Failure | Likelihood | Impact | Detection Time | Recovery Time | Primary Mitigation |
|---------|-----------|--------|---------------|---------------|-------------------|
| Queue Overload | Medium | Critical | 2 minutes | 5 minutes | Auto-scaling + circuit breaker |
| Cache Failure | Low | Critical | 1 minute | 10 minutes | Sentinel failover + local LRU |
| External Timeout | High | High | 3 minutes | 1 minute | Aggressive timeouts + circuit breaker |

---

## Runbook Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│  ON-CALL RUNBOOK: URL Audit Service                         │
├─────────────────────────────────────────────────────────────┤
│  1. Check health:  curl /api/v1/health                      │
│  2. Check queue:   rabbitmqctl list_queues                  │
│  3. Check cache:   redis-cli ping                         │
│  4. Check workers: aws ecs describe-services              │
│  5. Check logs:    CloudWatch Logs → /aws/ecs/audit-api    │
│  6. Escalate:      #incidents Slack → PagerDuty if P1     │
└─────────────────────────────────────────────────────────────┘
```
