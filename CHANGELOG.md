# Changelog

All notable changes to k8s-iam-operator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [3.1.1](https://github.com/yannicksiewe/k8s-iam-operator/compare/v3.1.0...v3.1.1) (2026-03-01)

### Code Refactoring

* **ci:** push Docker images only on releases ([38f6230](https://github.com/yannicksiewe/k8s-iam-operator/commit/38f6230df36fc0c3abb1fe90c803266bc360c62e))

## [3.1.0](https://github.com/yannicksiewe/k8s-iam-operator/compare/v3.0.1...v3.1.0) (2026-03-01)

### Features

* **ci:** build and push Docker image with release version tag ([a955129](https://github.com/yannicksiewe/k8s-iam-operator/commit/a9551290a85cb3a3dd79e7ff33e131d65d75416a))

## [3.0.1](https://github.com/yannicksiewe/k8s-iam-operator/compare/v3.0.0...v3.0.1) (2026-03-01)

### Bug Fixes

* **ci:** add checkout step to image-scan job ([7970d35](https://github.com/yannicksiewe/k8s-iam-operator/commit/7970d35ccb91e6ee6fa88c8ac9dbbfce3334fd42))

# Changelog

All notable changes to this project will be documented in this file. See [standard-version](https://github.com/conventional-changelog/standard-version) for commit guidelines.

## 1.1.0 (2023-11-29)


### Features

* Build with alpine base image ([45929cb](https://github.com/yannicksiewe/k8s-iam-operator/commit/45929cbbee6a68dbf4a4083a77eec705948cd110))
* enabled metric for monitoring ([28f4503](https://github.com/yannicksiewe/k8s-iam-operator/commit/28f4503f12212ed8661bb09563ae39c6b741d5ee))
* Refactor Dockerfile, rename files, update imports, and add metrics endpoint. ([dab974f](https://github.com/yannicksiewe/k8s-iam-operator/commit/dab974fed545ee759409f7112bfb9511b2c37008))


### Bug Fixes

* Update log_config.py to set the logging level to ERROR. ([c31ccc3](https://github.com/yannicksiewe/k8s-iam-operator/commit/c31ccc300b47dc2edd33da5e17e0c075e1b51eff))

## 1.1.0 (2023-11-29)


### Features

* Build with alpine base image ([45929cb](https://github.com/yannicksiewe/k8s-iam-operator/commit/45929cbbee6a68dbf4a4083a77eec705948cd110))
* enabled metric for monitoring ([28f4503](https://github.com/yannicksiewe/k8s-iam-operator/commit/28f4503f12212ed8661bb09563ae39c6b741d5ee))
* Refactor Dockerfile, rename files, update imports, and add metrics endpoint. ([dab974f](https://github.com/yannicksiewe/k8s-iam-operator/commit/dab974fed545ee759409f7112bfb9511b2c37008))


### Bug Fixes

* Update log_config.py to set the logging level to ERROR. ([c31ccc3](https://github.com/yannicksiewe/k8s-iam-operator/commit/c31ccc300b47dc2edd33da5e17e0c075e1b51eff))

## 1.1.0 (2023-11-29)


### Features

* Build with alpine base image ([45929cb](https://github.com/yannicksiewe/k8s-iam-operator/commit/45929cbbee6a68dbf4a4083a77eec705948cd110))
* enabled metric for monitoring ([28f4503](https://github.com/yannicksiewe/k8s-iam-operator/commit/28f4503f12212ed8661bb09563ae39c6b741d5ee))
* Refactor Dockerfile, rename files, update imports, and add metrics endpoint. ([dab974f](https://github.com/yannicksiewe/k8s-iam-operator/commit/dab974fed545ee759409f7112bfb9511b2c37008))


### Bug Fixes

* Update log_config.py to set the logging level to ERROR. ([c31ccc3](https://github.com/yannicksiewe/k8s-iam-operator/commit/c31ccc300b47dc2edd33da5e17e0c075e1b51eff))

## [1.0.0] - 2023-09-25

### Added

- Kopf handlers for managing users, RBAC, groups, and roles in Kubernetes.
- Utility modules for user Kubeconfig generation.
- Utility modules for ServiceAccount creation and management.

## [0.1.0] - 2023-04-10

### Added

- Initial release of the k8s-iam-operator.
- Setup.py for project installation and configuration.
