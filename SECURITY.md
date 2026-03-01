# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 3.x     | :white_check_mark: |
| 2.x     | :x:                |
| < 2.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in k8s-iam-operator, please report it responsibly.

### How to Report

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Email the maintainers directly with details of the vulnerability
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- Acknowledgment of your report within 48 hours
- Regular updates on the status of the fix
- Credit in the release notes (unless you prefer anonymity)

## Security Best Practices

When deploying k8s-iam-operator, follow these security best practices:

### Container Security

The operator container is configured with:
- Non-root user (UID 1000)
- Read-only root filesystem
- All capabilities dropped
- No privilege escalation

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
```

### RBAC

The operator requires cluster-wide RBAC permissions. Use the minimal ClusterRole provided in the Helm chart.

**Recommendations:**
- Deploy the operator in a dedicated namespace
- Use NetworkPolicies to restrict traffic
- Enable PodSecurityPolicy/Pod Security Standards
- Regularly audit operator activities using the audit logs

### Input Validation

The operator validates all CRD inputs:
- DNS-compliant names (max 63 characters)
- Valid RBAC verbs only
- Namespace injection prevention
- Length limits on all fields

### Audit Logging

Enable audit logging for compliance:
```yaml
audit:
  enabled: true
```

Audit logs capture:
- All RBAC create/update/delete operations
- Timestamps
- Resource details
- Operation status

### Network Policies

Enable network policies in production:
```yaml
networkPolicy:
  enabled: true
```

This restricts:
- Ingress to health/metrics port only
- Egress to Kubernetes API and DNS only

### Secret Handling

- Service account tokens are stored in Kubernetes Secrets
- Kubeconfig secrets use the `kubernetes.io/kubeconfig` type
- Never log sensitive data

## Security Updates

Security updates are released as patch versions. Subscribe to releases to receive notifications.

## Dependencies

We regularly update dependencies to address security vulnerabilities. Run `pip list --outdated` to check for updates.
