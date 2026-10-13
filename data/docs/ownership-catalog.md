# Service Ownership Catalog & Team Responsibilities

## Team Roster & Service Matrix

### 1. Payments Engineering
- **Team Lead**: Sarah Chen (`sarah.chen@northstar.internal`)
- **Slack**: `#team-payments`
- **Owned Services**:
  - `checkout-api` (Northstar orchestrator)
  - `payment-gateway-adapter` (Stripe/Adyen connectivity)
- **Repositories**: `github.com/northstar/checkout-api`, `github.com/northstar/payment-gateway-adapter`
- **On-Call Alias**: `payments-oncall`

### 2. Core Platform Engineering
- **Team Lead**: Elena Rostova (`elena.rostova@northstar.internal`)
- **Slack**: `#team-core-platform`
- **Owned Services**:
  - `pricing-service` (Discounts, taxes, currency conversion)
- **Repositories**: `github.com/northstar/pricing-service`
- **On-Call Alias**: `platform-oncall`

### 3. Risk & Trust Engineering
- **Team Lead**: Marcus Vance (`marcus.vance@northstar.internal`)
- **Slack**: `#team-risk-engineering`
- **Owned Services**:
  - `fraud-service` (Real-time velocity scoring, 3DS challenges)
- **Repositories**: `github.com/northstar/fraud-service`
- **On-Call Alias**: `risk-oncall`

### 4. Data Platform & Infrastructure
- **Team Lead**: Vikram Patel (`vikram.patel@northstar.internal`)
- **Slack**: `#team-datainfra`
- **Owned Services**:
  - `order-db-proxy` (PostgreSQL connection pooler and partitioner)
- **Repositories**: `github.com/northstar/order-db-proxy`
- **On-Call Alias**: `dataplatform-oncall`

### 5. Customer Communications
- **Team Lead**: Devin Lee (`devin.lee@northstar.internal`)
- **Slack**: `#team-customer-comms`
- **Owned Services**:
  - `notification-worker` (Kafka consumer for email/SMS notifications)
- **Repositories**: `github.com/northstar/notification-worker`
- **On-Call Alias**: `comms-oncall`
