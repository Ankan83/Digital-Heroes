# ADR-003: Database Technology Decision

## Status
Accepted

## Context
The service needs persistent storage for:
- Audit history (URL, status, timestamp, metadata)
- Analytics queries (top URLs, error rates, response time percentiles)
- Customer billing data (audit counts per API key)

## Decision
We will use **PostgreSQL (AWS RDS Multi-AZ)**.

## Alternatives Considered

### Alternative A: MongoDB
- **Pros**: Flexible schema for varying audit metadata, easy horizontal scaling with sharding
- **Cons**: Weaker consistency guarantees, complex aggregation pipelines, higher memory usage
- **Rejected because**: Audit records have a strict, well-defined schema. PostgreSQL's JSONB handles flexible metadata while maintaining ACID. Relational queries (JOINs, window functions) are essential for analytics.

### Alternative B: DynamoDB
- **Pros**: Fully managed, infinite scale, single-digit ms latency
- **Cons**: No complex queries (no JOINs, limited aggregation), eventual consistency by default, expensive for scan operations
- **Rejected because**: We need time-series analytics (p99 latency over 7 days). DynamoDB requires duplicating data into multiple access patterns or using Athena/Glue, adding complexity.

### Alternative C: ClickHouse / TimescaleDB
- **Pros**: Optimized for time-series data, columnar storage for fast aggregations
- **Cons**: Overkill for 10K/day, adds another database to maintain
- **Rejected because**: PostgreSQL with proper indexing handles 10K/day easily. We can add TimescaleDB extension later if needed.

## Consequences
- **Positive**: ACID compliance, mature ecosystem, JSONB for flexibility, read replicas for analytics
- **Negative**: Vertical scaling limit (mitigated by read replicas and connection pooling with PgBouncer)
- **Migration path**: Can partition old data to S3 (cold storage) after 90 days

## Decision Date
2024-01-15
