# ADR-001: Cache Technology Decision

## Status
Accepted

## Context
The URL Audit Service needs a caching layer to store audit results and avoid redundant HTTP requests to external websites. The cache must support:
- Sub-millisecond reads for SLA compliance
- TTL-based expiration
- Distributed access across multiple API nodes
- High availability

## Decision
We will use **Redis Cluster** (AWS ElastiCache) as the primary caching layer.

## Alternatives Considered

### Alternative A: Memcached
- **Pros**: Simpler protocol, slightly lower latency for simple GET/SET
- **Cons**: No persistence, no replication, no pub/sub for cache invalidation, no data structures beyond key-value
- **Rejected because**: We need replication for HA and pub/sub for cache invalidation events. Memcached is a dead-end for future features like rate limiting or leaderboards.

### Alternative B: In-Memory Cache (per node)
- **Pros**: Zero network latency, no infrastructure cost
- **Cons**: Cache inconsistency across nodes, lost on restart, no shared state
- **Rejected because**: At 500 concurrent requests across 3+ nodes, cache hit rate would plummet due to request distribution. Requires sticky sessions which complicate load balancing.

### Alternative C: DynamoDB DAX
- **Pros**: Fully managed, integrates with AWS IAM
- **Cons**: Higher latency (~ms vs sub-ms), overkill for simple TTL caching, vendor lock-in
- **Rejected because**: Redis is the industry standard for this use case. DAX adds complexity without benefit for our data model.

## Consequences
- **Positive**: Sub-ms reads, pub/sub for real-time invalidation, proven at scale
- **Negative**: Requires managing cluster topology (mitigated by ElastiCache)
- **Migration path**: Can switch to KeyDB (Redis-compatible, multi-threaded) if single-threaded Redis becomes a bottleneck

## Decision Date
2024-01-15
