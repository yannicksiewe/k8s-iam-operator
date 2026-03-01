# Release Process

This project uses **automated releases** via [semantic-release](https://semantic-release.gitbook.io/).

## How Releases Work

Releases are triggered automatically when commits are pushed to `main`. The version bump is determined by commit message prefixes following [Conventional Commits](https://www.conventionalcommits.org/).

### Commit Types and Version Bumps

| Commit Prefix | Version Bump | Example |
|--------------|--------------|---------|
| `feat:` | Minor (3.1.0 → 3.2.0) | `feat: add OIDC authentication` |
| `fix:` | Patch (3.1.0 → 3.1.1) | `fix: resolve token validation bug` |
| `perf:` | Patch | `perf: optimize reconciliation loop` |
| `refactor:` | Patch | `refactor: simplify user service` |
| `BREAKING CHANGE` | Major (3.1.0 → 4.0.0) | See below |

### Commits That Don't Trigger Releases

| Commit Prefix | Effect |
|--------------|--------|
| `chore:` | No release |
| `docs:` | No release (except README) |
| `style:` | No release |
| `test:` | No release |
| `ci:` | No release |

## Triggering a Release

### Automatic (Recommended)

Simply push commits with the appropriate prefix:

```bash
# Patch release (bug fix)
git commit -m "fix: correct RBAC binding logic"
git push origin main

# Minor release (new feature)
git commit -m "feat: add namespace quota support"
git push origin main

# Major release (breaking change)
git commit -m "feat: redesign CRD schema

BREAKING CHANGE: User CRD spec.role renamed to spec.roleRef"
git push origin main
```

### Manual Trigger (Force Release)

If you need to force a release without code changes:

```bash
git commit --allow-empty -m "feat: trigger release"
git push origin main
```

## What Happens During Release

When a release is triggered, the CI pipeline:

1. ✅ Runs all tests (unit, integration)
2. ✅ Runs security scans (Trivy)
3. ✅ Lints Helm chart
4. ✅ Determines new version from commits
5. ✅ Updates `CHANGELOG.md`
6. ✅ Updates `app/version.py`
7. ✅ Updates `charts/k8s-iam-operator/Chart.yaml`
8. ✅ Creates git tag (e.g., `v3.2.0`)
9. ✅ Creates GitHub release with notes
10. ✅ Builds and pushes Docker image:
    - `quay.io/yannick_siewe/k8s-iam-operator:v3.2.0`
    - `quay.io/yannick_siewe/k8s-iam-operator:latest`

## Pre-Release Checklist

Before pushing release-triggering commits:

- [ ] All tests pass locally: `pytest tests/`
- [ ] Linting passes: `flake8 app/ tests/`
- [ ] Helm chart lints: `helm lint charts/k8s-iam-operator`
- [ ] No high/critical CVEs: `trivy fs .`
- [ ] Documentation updated for new features
- [ ] Breaking changes documented in commit message

## Post-Release Verification

After release completes:

- [ ] Verify GitHub release: https://github.com/yannicksiewe/k8s-iam-operator/releases
- [ ] Verify Docker image: `docker pull quay.io/yannick_siewe/k8s-iam-operator:v3.x.x`
- [ ] Verify Helm chart version matches

```bash
# Check versions match
docker run --rm quay.io/yannick_siewe/k8s-iam-operator:latest python -c "from app.version import __version__; print(__version__)"
```

## Hotfix Process

For urgent fixes to a released version:

```bash
# 1. Create fix on main with fix: prefix
git commit -m "fix: critical security vulnerability in auth"
git push origin main
# This automatically creates a patch release
```

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes to CRDs, APIs, or Helm values
- **MINOR** (0.X.0): New features, backward compatible
- **PATCH** (0.0.X): Bug fixes, security patches, backward compatible

### Breaking Changes Include

- CRD schema changes requiring migration
- Removed or renamed CRD fields
- Changed default values affecting behavior
- Removed Helm values
- API behavior changes

## Troubleshooting

### Release Not Triggered

1. Check commit message follows conventional commits format
2. Verify commit was pushed to `main` branch
3. Check CI logs for semantic-release output
4. Ensure commits have release-triggering prefixes (`feat:`, `fix:`)

### Version Not Bumped Correctly

1. Check commit message format is correct
2. For major bumps, ensure `BREAKING CHANGE` is in commit body (not subject)
3. Review `.releaserc.yml` for release rules

## Contacts

- **Repository**: https://github.com/yannicksiewe/k8s-iam-operator
- **Releases**: https://github.com/yannicksiewe/k8s-iam-operator/releases
- **Container Registry**: https://quay.io/repository/yannick_siewe/k8s-iam-operator
