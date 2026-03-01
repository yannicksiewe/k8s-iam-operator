# Service Level Objectives (SLOs)

This document defines the Service Level Objectives for k8s-iam-operator in production environments.

## Overview

SLOs define the target reliability for the operator. These objectives help:
- Set expectations for users
- Guide operational decisions
- Inform capacity planning
- Define alerting thresholds

## SLO Definitions

### 1. Availability SLO

**Target: 99.9% availability**

| Window | Allowed Downtime |
|--------|-----------------|
| Daily | 1.44 minutes |
| Weekly | 10.08 minutes |
| Monthly | 43.8 minutes |
| Quarterly | 2.19 hours |
| Yearly | 8.76 hours |

#### Definition

Availability is measured as the percentage of time the operator is able to process reconciliation requests.

```promql
# Availability calculation
(
  sum(rate(kopf_handler_duration_seconds_count[5m])) /
  (sum(rate(kopf_handler_duration_seconds_count[5m])) + sum(rate(kopf_handler_errors_total[5m])))
) * 100
```

#### What Counts as Downtime

- All operator pods are unavailable
- Operator cannot connect to Kubernetes API
- All reconciliation attempts fail

#### What Doesn't Count as Downtime

- Single pod restart during rolling update
- Planned maintenance with proper notification
- External dependencies (etcd, API server) failures

### 2. Reconciliation Latency SLO

**Target: P99 latency < 30 seconds**

| Percentile | Target |
|------------|--------|
| P50 | < 5s |
| P95 | < 15s |
| P99 | < 30s |

#### Definition

Reconciliation latency is the time from when a CR change is detected to when the reconciliation completes.

```promql
# P99 latency
histogram_quantile(0.99, sum(rate(kopf_handler_duration_seconds_bucket[5m])) by (le))
```

#### Exclusions

- Initial bulk reconciliation on operator startup
- Resources with complex role hierarchies
- External API delays (cloud provider IAM)

### 3. Error Rate SLO

**Target: < 0.1% error rate**

| Window | Max Errors (per 1000 operations) |
|--------|----------------------------------|
| Hourly | 1 |
| Daily | 10 |
| Weekly | 70 |

#### Definition

Error rate is the percentage of reconciliation attempts that fail.

```promql
# Error rate calculation
(
  sum(rate(kopf_handler_errors_total[5m])) /
  sum(rate(kopf_handler_duration_seconds_count[5m]))
) * 100
```

#### What Counts as Errors

- Unhandled exceptions in handlers
- Kubernetes API errors (non-transient)
- Invalid resource specifications
- RBAC permission failures

#### What Doesn't Count as Errors

- Transient API errors that succeed on retry
- Rate limiting (429 responses)
- Resource validation failures (user error)

## Error Budget

### Calculation

Error budget = 100% - SLO target

| SLO | Target | Error Budget |
|-----|--------|--------------|
| Availability | 99.9% | 0.1% |
| Latency | 99% | 1% |
| Error Rate | 99.9% | 0.1% |

### Error Budget Policy

#### When Budget is Healthy (> 50% remaining)

- Continue normal development pace
- Deploy new features
- Perform non-urgent maintenance

#### When Budget is Degraded (25-50% remaining)

- Prioritize reliability work
- Increase testing coverage
- Review recent changes for regressions

#### When Budget is Critical (< 25% remaining)

- Freeze non-critical deployments
- Focus exclusively on reliability
- Conduct incident reviews
- Increase monitoring coverage

#### When Budget is Exhausted (0% remaining)

- Stop all deployments except reliability fixes
- Conduct thorough incident analysis
- Implement preventive measures
- Review and potentially revise SLOs

## Monitoring and Alerting

### Key Metrics

| Metric | SLO | Alert Threshold |
|--------|-----|-----------------|
| Availability | 99.9% | < 99.5% for 5m |
| P99 Latency | 30s | > 30s for 10m |
| Error Rate | 0.1% | > 1% for 5m |

### Alert Examples

```yaml
# Availability alert
- alert: IAMOperatorAvailabilityBudgetBurn
  expr: |
    (
      1 - (
        sum(rate(kopf_handler_duration_seconds_count[1h])) /
        (sum(rate(kopf_handler_duration_seconds_count[1h])) + sum(rate(kopf_handler_errors_total[1h])))
      )
    ) > (1 - 0.999) * 14.4
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High error budget burn rate for availability"

# Latency alert
- alert: IAMOperatorLatencyBudgetBurn
  expr: |
    histogram_quantile(0.99, sum(rate(kopf_handler_duration_seconds_bucket[1h])) by (le)) > 30
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "P99 latency exceeds SLO"
```

## SLI/SLO Dashboard

### Recommended Panels

1. **Availability over time** (7-day rolling)
2. **Error budget remaining** (monthly)
3. **Latency percentiles** (P50, P95, P99)
4. **Error rate trend**
5. **SLO compliance status**

### Example Grafana Queries

```promql
# Current availability (7-day)
avg_over_time((
  sum(rate(kopf_handler_duration_seconds_count[5m])) /
  (sum(rate(kopf_handler_duration_seconds_count[5m])) + sum(rate(kopf_handler_errors_total[5m])))
)[7d:])

# Error budget remaining (monthly)
(0.001 - (
  sum(increase(kopf_handler_errors_total[30d])) /
  sum(increase(kopf_handler_duration_seconds_count[30d]))
)) / 0.001 * 100

# P99 latency (5-minute)
histogram_quantile(0.99, sum(rate(kopf_handler_duration_seconds_bucket[5m])) by (le))
```

## Reporting

### Weekly SLO Report

Include:
- SLO compliance status
- Error budget consumption
- Incident summary
- Top error sources
- Action items

### Monthly SLO Review

Review:
- SLO target appropriateness
- Error budget policy effectiveness
- Capacity vs. demand trends
- SLO revision proposals

## SLO Revision Process

SLOs should be reviewed quarterly and may be revised when:

1. Current SLOs are consistently exceeded (tighten)
2. Current SLOs are unachievable (loosen)
3. Business requirements change
4. New capabilities are added

### Revision Procedure

1. Propose new SLO with justification
2. Review historical data
3. Assess impact on users
4. Update alerting thresholds
5. Communicate changes to stakeholders
6. Update documentation

## Appendix: Metric Definitions

### kopf_handler_duration_seconds

Histogram of handler execution time in seconds.

Labels:
- `handler`: Handler function name
- `cause`: Trigger cause (create, update, delete)

### kopf_handler_errors_total

Counter of handler errors.

Labels:
- `handler`: Handler function name
- `exception`: Exception type

### up

Standard Prometheus up metric for target availability.

Labels:
- `job`: Service name
- `instance`: Pod instance
