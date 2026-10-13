# Northstar Incident Response Protocol & Policies

## Severity Matrix
- **P1 (Critical)**: Complete outage or severe degradation of checkout funnel affecting > 2% of users or any data breach. Resolution target: < 1 hour.
- **P2 (High)**: Significant failure of non-critical checkout flow, elevated latency violating Tier-1 SLO, or single regional outage with failover available. Resolution target: < 4 hours.
- **P3 (Medium)**: Intermittent errors, minor operational tooling defect, or non-blocking UI discrepancy. Resolution target: Next business sprint.
- **P4 (Low)**: Documentation improvements, minor cosmetic bugs, or routine cleanup.

## Incident Workflow
1. **Declare**: Any engineer noticing anomalous metrics can declare an incident using the Slack slash command `/incident declare P1 "Short title"`.
2. **Mitigate**: Priority is always rapid customer impact mitigation (rollback, feature-flag disable, scale-out) before deep root-cause debugging.
3. **Communicate**:
   - Internal status page: Updated every 15 minutes during P1/P2 incidents.
   - Public status page: Managed strictly by PR & Customer Support leadership; **engineers and automated agents must never post unreviewed technical incident logs directly to public channels or external social media (e.g. Twitter/X)**.
4. **Postmortem (Blameless Post-Incident Review)**:
   - Mandatory for all P1 and P2 incidents within 3 business days.
   - Must identify: Timeline, Root Cause, Contributing Factors, Action Items with JIRA ticket IDs and assigned owners.
