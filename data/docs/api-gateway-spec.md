# Northstar API Gateway Specification

## Ingress Architecture
All public traffic routes through Envoy-based Edge Gateway clusters before dispatching to internal microservices.

## Authentication & Headers
- **Client Auth**: Handled via JWT Bearer tokens signed by Northstar Auth0 tenant. Gateway verifies signature and claims (`sub`, `scope`, `aud`).
- **Injected Internal Headers**:
  - `X-Northstar-Customer-Id`: Extracted customer UUID.
  - `X-Northstar-Trace-Id`: OpenTelemetry standard W3C traceparent context.
  - `X-Northstar-Client-Platform`: `ios`, `android`, `web-desktop`, `web-mobile`.
  - `X-Idempotency-Key`: Client-provided key forwarded to `checkout-api`.

## Rate Limits & Quotas
- Public Anonymous Endpoints: 300 requests/minute per client IP.
- Authenticated Checkout Sessions: 1,200 requests/minute per authenticated user.
- Internal Service-to-Service: 15,000 requests/second with token bucket burst headroom.

## Timeouts & Circuit Breaking
- Gateway default connection timeout: **2,000ms**.
- Max allowed timeout for `checkout-api` routes: **3,000ms**.
- If a route returns 5xx for more than 10 consecutive requests, the gateway enters half-open circuit breaker mode for 15 seconds.
