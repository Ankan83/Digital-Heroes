# ADR-002: Message Queue Technology Decision

## Status
Accepted

## Context
The service needs a message queue to decouple API requests from audit execution. Requirements:
- Durable message storage (don't lose audits)
- Priority queues (VIP customers vs free tier)
- Dead Letter Exchange for failed jobs
- Exactly-once semantics
- Horizontal scaling of workers

## Decision
We will use **RabbitMQ with Quorum Queues**.

## Alternatives Considered

### Alternative A: Apache Kafka
- **Pros**: Industry standard for event streaming, extremely high throughput (>100K msg/sec), log-based retention
- **Cons**: Overkill for 10K/day, complex ops (ZooKeeper/KRaft), higher latency for small messages, no built-in priority queues
- **Rejected because**: Our throughput is low. Kafka shines at >100K msg/sec. The operational overhead (partition rebalancing, consumer groups) is unjustified for our scale.

### Alternative B: AWS SQS
- **Pros**: Fully managed, no servers to maintain, integrates with Lambda
- **Cons**: No native priority queues, 15-minute visibility timeout limit, message size limit 256KB, no DLX routing flexibility
- **Rejected because**: We need priority lanes for SLA tiers. SQS FIFO is too expensive and limited for this use case.

### Alternative C: Redis Streams
- **Pros**: Already have Redis infrastructure, simple to implement
- **Cons**: Not truly durable (memory-only), no advanced routing, consumer group management is primitive
- **Rejected because**: Redis is a cache, not a queue. Using it for both creates coupling and risks eviction of queue data under memory pressure.

## Consequences
- **Positive**: Built-in priority queues, flexible routing with exchanges, mature DLX, quorum queues for HA
- **Negative**: Requires RabbitMQ expertise for clustering and tuning
- **Migration path**: Can migrate to Kafka later if throughput grows >100K/day

## Decision Date
2024-01-15
