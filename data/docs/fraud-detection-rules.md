# Fraud Detection Engine Rules & Scoring Policies

## Risk Score Calibration
`fraud-service` outputs a normalized float score between 0.0 and 100.0 for every transaction request evaluated:

- **0.0 - 49.9 (Low Risk / Auto-Approve)**:
  - Immediate pass through to `payment-gateway-adapter`.
  - No customer challenge required.
- **50.0 - 84.9 (Medium Risk / 3DS Step-Up Challenge)**:
  - Requires customer 3D-Secure (3DS) SMS or biometric cardholder authentication.
  - Note: PR #102 proposes raising the challenge threshold to 78 for low-ticket transactions (< $50) to lower cart abandonment.
- **85.0 - 100.0 (High Risk / Hard Reject)**:
  - Transaction automatically blocked with error code `ERR_FRAUD_VELOCITY_BREACH`.
  - Customer card token flagged for manual review queue in Zendesk Risk Portal.

## Evaluated Features
1. **IP Velocity**: Number of distinct email attempts from single subnet in 10 minutes (Threshold: max 4).
2. **Device Fingerprint Mismatch**: Browser canvas fingerprint divergence from user profile history.
3. **Cardholder Geolocation**: Distance between billing ZIP code and IP geolocation > 1,500km triggers +25 risk points.

## Emergency Overrides
In the event of an active DDoS or algorithmic false positive storm:
- On-call engineer can invoke the command:
  `vault write secret/fraud/override mode="shadow"`
  which logs all risk scores to Kafka but approves all valid payments without step-up authentication.
