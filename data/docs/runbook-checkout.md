# Runbook: Checkout API Troubleshooting & Emergency Operations

## Target Service: `checkout-api`
- **Owner**: Payments Engineering (`payments@northstar.internal`)
- **Primary Dashboard**: Grafana `dashboards/checkout-overview`
- **Alert Channel**: `#checkout-alerts` (Slack)

## Common Failure Modes & Remediation

### 1. Elevated HTTP 504 Gateway Timeouts
- **Symptoms**: Customer checkout rate drops, 504 count surges above 1% of total traffic.
- **Root Causes**:
  - `payment-gateway-adapter` blocked on slow upstream acquirers.
  - Connection pool exhaustion on `order-db-proxy`.
- **Diagnostic Steps**:
  1. Check Prometheus metric `rate(http_requests_total{service="checkout-api", status=~"504"}[5m])`.
  2. Inspect trace spans for the longest bottleneck child component in OpenTelemetry.
  3. If acquirer timeouts exceed 1500ms, enable gateway backoff retry or failover to secondary acquirer.
- **Remediation**:
  - Scale out `checkout-api` deployment:
    ```bash
    kubectl scale deployment checkout-api --replicas=15 -n production
    ```
  - If upstream acquirer is down, toggle the secondary payment gateway switch via feature flag:
    `launchdarkly: payments.enable_secondary_acquirer_failover = true`.

### 2. High Error Rate in Fraud Verification
- **Symptoms**: Checkouts are rejected or hanging at `POST /v1/checkout/sessions/{id}/authorize`.
- **Diagnostic Steps**:
  - Run `kubectl logs -l app=fraud-service --tail=200 -n production | grep ERROR`.
  - Check if fraud service latency P99 > 300ms.
- **Remediation**:
  - Switch fraud evaluation to **shadow mode** (bypass hard blocks for low-risk tier):
    `vault write secret/checkout/fraud_mode value="shadow"`.
  - Notify `risk-oncall` on Slack channel `#risk-war-room`.

### 3. Graceful Degradation Policies
- When `pricing-service` is unreachable, `checkout-api` serves cached catalogue prices with a maximum price-staleness flag of 15 minutes.
- If order notifications lag, Kafka buffering guarantees zero loss; do NOT restart Kafka brokers without consulting `dataplatform-oncall`.
