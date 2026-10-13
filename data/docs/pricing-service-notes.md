# Pricing Service Technical Notes & Cache Architecture

## Caching Strategy
`pricing-service` serves over 25,000 queries per second during peak hours. To maintain its **99.95% availability SLO** and **120ms P99 latency target**, it implements a multi-tier caching hierarchy:

1. **L1 In-Memory LRU**:
   - Cache size: 50,000 items per pod instance.
   - TTL: 60 seconds.
   - Purpose: Extreme hot-item price protection during celebrity endorsements or viral promotions.

2. **L2 Redis Cluster**:
   - Engine: Redis 7.2 on AWS ElastiCache.
   - Cluster configuration: 3 primary shards, 2 read replicas each.
   - TTL: 300 seconds (5 minutes).
   - Invalidation: Cache invalidation events emitted via Kafka topic `catalog.pricing.events` when merchandise teams update prices in the CMS.

## Currency Conversions
- FX rates are synced every 6 hours from the central European Central Bank (ECB) feed.
- Supported currency pairs: USD, EUR, GBP, CAD, AUD, JPY.
- If FX sync fails, system falls back to the previous day's rate with an emitted warning log: `WARN [pricing-fx] Stale exchange rates in use`.

## Degraded Fallback Mode
If Redis cluster connectivity drops, `pricing-service` activates local fallback mode using read-only database replicas via `order-db-proxy`. Latency increases to ~85ms, but error rates remain under 0.01%.
