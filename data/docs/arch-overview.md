# Northstar Checkout Architecture Overview

## Executive Summary
Northstar Checkout is the mission-critical checkout and order processing platform powering Northstar e-commerce. It processes millions of orders daily, orchestrating customer shopping carts, dynamic promotional pricing, real-time risk assessment, and payment processing.

## Service Topology
The platform consists of microservices communicating over gRPC for internal RPC and REST/JSON for client-facing endpoints:

1. **`checkout-api`**:
   - Primary tier-1 orchestrator.
   - Handles client checkout sessions (`POST /v1/checkout/sessions`).
   - Coordinates sequential and parallel calls to `pricing-service`, `fraud-service`, and `payment-gateway-adapter`.
   - Availability SLO: **99.9%**; P99 latency target: **350ms**.

2. **`pricing-service`**:
   - Calculates item discounts, bundle coupons, localized tax rates, and currency conversions.
   - Relies on Redis cluster for fast caching (TTL 300s) and reads catalog data via `order-db-proxy`.
   - Availability SLO: **99.95%**; P99 latency target: **120ms**.

3. **`fraud-service`**:
   - Assesses risk for transactions before payment authorization.
   - Evaluates device fingerprints, velocity heuristics, and ML scoring. Returns a score between 0 and 100.
   - Availability SLO: **99.9%**; P99 latency target: **200ms**.

4. **`payment-gateway-adapter`**:
   - Communicates with external credit card acquirers and alternative payment methods.
   - Implements idempotent transaction IDs to avoid double charges.
   - Availability SLO: **99.99%**; P99 latency target: **800ms**.

5. **`order-db-proxy`**:
   - Tier-0 database proxy pooling connections to PostgreSQL shards.
   - Availability SLO: **99.99%**; P99 latency target: **50ms**.

6. **`notification-worker`**:
   - Consumes Kafka events for completed orders to dispatch customer receipts and shipping alerts.
   - Availability SLO: **99.5%**; P99 latency target: **1500ms**.

## Communication & Resilience Patterns
- **Idempotency**: All payment and checkout mutation endpoints require an `X-Idempotency-Key` header (UUIDv4). Keys are cached in Redis with a 24-hour expiration.
- **Circuit Breakers**: When downstream services (e.g. `fraud-service` or acquirers) exceed a 5% error threshold over 10 seconds, `checkout-api` trips the circuit breaker and triggers fallback degradation modes.
- **Data Consistency**: Checkout records follow an outbox pattern, writing to the transactional database first, then publishing asynchronous events to Kafka topics.
