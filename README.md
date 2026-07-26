# URL Audit Service

Production-grade URL auditing service with full system design documentation for scale.

---

## Task A — Production-Grade Page Pulse

A production-ready URL Audit Service built with **FastAPI** and **Python**.

### Features

- **Production-ready API** with input validation, timeouts, and concurrency controls
- **Redis caching** with configurable TTL for audit results (falls back to in-memory)
- **Per-client rate limiting** using token bucket algorithm
- **Structured logging** with unique Request IDs for every request
- **SSRF protection** blocking internal/reserved IP addresses
- **Graceful shutdown** and health check endpoints
- **Interactive HTML UI** at the root endpoint
- **Comprehensive test suite** — 23 tests covering API, validator, caching, rate limiting
- **CI/CD** via GitHub Actions

### Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI 0.103.2 |
| HTTP Client | httpx |
| Cache | Redis (with in-memory fallback) |
| Rate Limiting | Custom token bucket |
| Validation | Pydantic v1 + custom URL validator |
| Testing | pytest + pytest-asyncio + pytest-cov |
| Deployment | Docker + Docker Compose |

### Project Structure (Task A)

```
├── app/                        ← Backend application
│   ├── main.py                 # FastAPI entry point
│   ├── api/
│   │   ├── middleware.py       # Request ID, logging, rate limiting, CORS, timeout
│   │   └── routes.py           # API endpoints
│   ├── core/
│   │   ├── config.py           # Environment-based configuration
│   │   └── logging.py          # Structured logging with request IDs
│   ├── services/
│   │   └── audit_service.py    # Core audit logic with concurrency control
│   └── utils/
│       ├── validator.py        # URL validation + SSRF protection
│       ├── cache.py            # Redis + in-memory cache
│       └── rate_limiter.py     # Token bucket rate limiter
├── static/                     ← Frontend assets
│   ├── index.html
│   ├── css/style.css
│   └── js/script.js
├── tests/                      ← Test suite
│   ├── test_api.py
│   └── test_validator.py
├── .github/workflows/ci.yml    ← GitHub Actions CI
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Interactive HTML UI |
| `/api/v1/audit` | POST | Audit a URL |
| `/api/v1/health` | GET | Health check |

### Running Locally

```bash
# With Python (no Redis needed)
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
python -m app.main
# Open http://localhost:8080

# With Docker Compose (includes Redis)
docker-compose up --build

# Run tests
pytest -v
pytest --cov=app --cov-report=term-missing -v
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | Server port |
| `HOST` | `0.0.0.0` | Server host |
| `REDIS_HOST` | `localhost` | Redis server host |
| `REDIS_PORT` | `6379` | Redis server port |
| `CACHE_TTL_SECONDS` | `300` | Cache duration in seconds |
| `RATE_LIMIT_PER_MINUTE` | `60` | Requests per minute per IP |
| `RATE_LIMIT_BURST` | `10` | Burst capacity |
| `AUDIT_TIMEOUT_SECONDS` | `10` | HTTP audit timeout |
| `MAX_CONCURRENCY` | `100` | Max concurrent audits |
| `LOG_LEVEL` | `INFO` | Log level |
| `ENVIRONMENT` | `development` | Environment name |

---

## Task B — Design It for Scale

System design documentation for scaling the URL Audit Service to **10,000 audits/day** with **500 concurrent requests** and a customer-facing SLA.

### Deliverables

| Document | Location | Description |
|----------|----------|-------------|
| **Architecture Document** | [`docs/architecture.md`](docs/architecture.md) | Components, data flow, queueing strategy, state management |
| **Architecture Diagram** | [`diagrams/architecture-diagram.png`](diagrams/architecture-diagram.png) | Visual system architecture |
| **Technology Decision Record** | [`docs/adr/`](docs/adr/) | 3 ADRs covering cache, queue, and database choices |
| **Failure Mode Analysis** | [`docs/failure-modes.md`](docs/failure-modes.md) | 3 most likely failures with impact and mitigation |
| **Observability & Rollback** | [`docs/operations.md`](docs/operations.md) | Metrics, alerts, dashboards, rollback strategy |

### Architecture Overview

```
Client → Cloudflare CDN → API Gateway (Kong) → FastAPI Nodes → Redis Cache
                                                      ↓
                                              RabbitMQ Queue
                                                      ↓
                                              Worker Pool → PostgreSQL → S3 Logs
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Cache** | Redis Cluster | Sub-ms reads, pub/sub invalidation, proven at scale |
| **Queue** | RabbitMQ Quorum | Priority queues, DLX, exactly-once, simpler than Kafka |
| **Database** | PostgreSQL RDS | ACID compliance, JSONB flexibility, relational analytics |
| **Workers** | ECS Fargate | No cold starts, predictable pricing, auto-scaling |
| **API Gateway** | Kong | Plugin ecosystem, no vendor lock-in, lower latency |

### Scaling Targets

| Metric | Target |
|--------|--------|
| Daily audits | 10,000 |
| Peak concurrent | 500 |
| Response time p99 | < 2s |
| Cache hit rate | > 80% |
| Availability | 99.9% |

### Failure Resilience

| Failure | Impact | Mitigation |
|---------|--------|------------|
| **Queue Overload** | SLA breach, memory exhaustion | Auto-scaling workers, circuit breaker, traffic shedding |
| **Cache Failure** | 10x latency spike, cascading timeouts | Redis Sentinel failover, local LRU fallback, graceful degradation |
| **External Timeout** | Worker exhaustion, queue buildup | Aggressive timeouts, circuit breaker per domain, separate thread pools |

### Operational Readiness

- **Metrics**: Prometheus + Grafana with 15+ key metrics
- **Alerts**: PagerDuty integration with P1/P2/P3 severity levels
- **Tracing**: AWS X-Ray with 1% sampling in production
- **Rollback**: Blue/green deployment with instant DNS flipback
- **Feature Flags**: LaunchDarkly for instant toggles without redeployment
- **Runbooks**: Documented 5-minute rollback procedure

### Cost Estimate

| Component | Monthly Cost (USD) |
|-----------|-------------------|
| ECS Fargate (API + Workers) | ~$150 |
| ElastiCache Redis | ~$50 |
| Amazon MQ (RabbitMQ) | ~$200 |
| RDS PostgreSQL Multi-AZ | ~$100 |
| S3 (logs) | ~$5 |
| Cloudflare Pro | ~$20 |
| **Total** | **~$525** |

---

## Footer Credit

The live application includes a visible footer:

> Built for [Digital Heroes Training Task](https://digitalheroesco.com)

---

## License

MIT
