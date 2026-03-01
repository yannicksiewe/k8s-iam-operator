# Release Checklist

This checklist should be followed for every release of k8s-iam-operator.

## Pre-Release

### Version Consistency

- [ ] Update `app/version.py` with new version
- [ ] Verify `charts/k8s-iam-operator/Chart.yaml` has matching `appVersion`
- [ ] Update `charts/k8s-iam-operator/Chart.yaml` version if chart changed
- [ ] Run version check:
  ```bash
  python -c "from app.version import __version__; print(__version__)"
  grep "appVersion:" charts/k8s-iam-operator/Chart.yaml
  ```

### Code Quality

- [ ] All tests pass: `make test`
- [ ] Linting passes: `make lint`
- [ ] Type checking passes: `mypy app/`
- [ ] Security scan passes: `trivy fs .`
- [ ] No high/critical CVEs in dependencies

### Documentation

- [ ] CHANGELOG.md updated with release notes
- [ ] README.md updated if needed
- [ ] API documentation updated for any CRD changes
- [ ] Upgrade guide updated with breaking changes
- [ ] Runbooks updated if alerting changed

### Testing

- [ ] Unit tests pass: `pytest tests/unit/`
- [ ] Integration tests pass: `pytest tests/integration/`
- [ ] Manual testing completed:
  - [ ] User creation
  - [ ] Group creation
  - [ ] Role creation
  - [ ] Kubeconfig generation
  - [ ] RBAC bindings
- [ ] Helm chart lints: `helm lint charts/k8s-iam-operator`
- [ ] Helm template renders: `helm template test charts/k8s-iam-operator`

### Compatibility

- [ ] Tested on minimum supported Kubernetes version
- [ ] Tested on latest supported Kubernetes version
- [ ] Helm 3.x compatibility verified
- [ ] Python 3.11+ compatibility verified

## Release Process

### Create Release

1. [ ] Create release branch (for major/minor):
   ```bash
   git checkout -b release/v3.x.x
   ```

2. [ ] Update version files (see above)

3. [ ] Commit version changes:
   ```bash
   git add app/version.py charts/k8s-iam-operator/Chart.yaml CHANGELOG.md
   git commit -m "chore: bump version to v3.x.x"
   ```

4. [ ] Create signed tag:
   ```bash
   git tag -s v3.x.x -m "Release v3.x.x"
   ```

5. [ ] Push release:
   ```bash
   git push origin release/v3.x.x
   git push origin v3.x.x
   ```

### CI Verification

- [ ] CI pipeline passes on tag
- [ ] Docker image built and scanned
- [ ] Image pushed to registry
- [ ] Helm chart packaged (if publishing)

### GitHub Release

1. [ ] Create GitHub release from tag
2. [ ] Add release notes from CHANGELOG
3. [ ] Attach any additional artifacts
4. [ ] Mark as pre-release if applicable

## Post-Release

### Verification

- [ ] Pull and verify released image:
  ```bash
  docker pull quay.io/yannick_siewe/k8s-iam-operator:v3.x.x
  ```

- [ ] Deploy to staging environment
- [ ] Run smoke tests
- [ ] Verify metrics and health endpoints

### Communication

- [ ] Announce release in relevant channels
- [ ] Update any external documentation
- [ ] Notify downstream consumers

### Housekeeping

- [ ] Merge release branch to main (if applicable)
- [ ] Update main branch version to next dev version
- [ ] Close release milestone
- [ ] Create next milestone

## Rollback Plan

If issues are discovered after release:

1. [ ] Identify scope of issue
2. [ ] If critical, create hotfix:
   ```bash
   git checkout -b hotfix/v3.x.y v3.x.x
   # fix issue
   git commit -m "fix: description"
   git tag -s v3.x.y -m "Hotfix v3.x.y"
   git push origin hotfix/v3.x.y v3.x.y
   ```

3. [ ] If non-critical, document in known issues
4. [ ] Communicate status to users

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (0.X.0): New features, backward compatible
- **PATCH** (0.0.X): Bug fixes, backward compatible

### Breaking Changes Include:

- CRD schema changes requiring migration
- Removed CRD fields
- Changed API behavior
- Removed Helm values
- Changed default values affecting behavior

### Version Examples

| Change | Before | After |
|--------|--------|-------|
| Bug fix | 3.0.0 | 3.0.1 |
| New feature | 3.0.1 | 3.1.0 |
| Breaking change | 3.1.0 | 4.0.0 |
| Security fix | 3.1.0 | 3.1.1 |

## Contacts

- **Release Manager**: @yannick-siewe
- **Security Contact**: security@example.com
- **Slack Channel**: #k8s-iam-operator
