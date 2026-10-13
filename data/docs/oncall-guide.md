# Northstar Engineering On-Call Guide

## Rotations & Handover
On-call rotations run weekly from Wednesday 10:00 UTC to Wednesday 10:00 UTC. Handover meetings occur in the `#ops-handover` channel.

## Active Rosters
| Team | Roster Name | Primary Slack | PagerDuty Schedule |
|---|---|---|---|
| Payments | `payments-oncall` | `#payments-oncall` | `sched-payments-tier1` |
| Core Platform | `platform-oncall` | `#core-platform` | `sched-platform-tier1` |
| Risk & Fraud | `risk-oncall` | `#risk-war-room` | `sched-risk-tier1` |
| Data Infrastructure | `dataplatform-oncall`| `#datainfra-alerts` | `sched-datainfra-tier0`|
| Customer Comms | `comms-oncall` | `#customer-comms` | `sched-comms-tier2` |

## Incident Paging Escalation Policy
1. **P1 (Critical Outage)**:
   - Primary engineer paged immediately via PagerDuty (phone call + push notification).
   - Must acknowledge within **5 minutes**.
   - If unacknowledged within 10 minutes, secondary engineer and Engineering Manager are paged.
   - Automatically opens an incident Slack room `#inc-YYYYMMDD-critical`.
2. **P2 (Major Degradation)**:
   - Primary engineer paged via push notification.
   - Must acknowledge within **15 minutes**.
3. **P3/P4 (Minor / Informational)**:
   - Ticket created in JIRA backlog; no nocturnal paging.

## Escalation Contacts
- Payments EM: Alex Rivera (`alex.rivera@northstar.internal`)
- Principal Architect: Dr. Marcus Vance (`marcus.vance@northstar.internal`)
- Incident Commander On-Duty: Pager alias `@incident-commander`
