# Makefile for k8s-iam-operator
#
# Usage:
#   make help        - Show this help
#   make lint        - Run linting
#   make test        - Run unit tests
#   make build       - Build Docker image
#   make run         - Run operator locally

.PHONY: help lint test test-coverage build run clean install-deps integration-test helm-lint helm-template

# Variables
PYTHON := python3
PIP := pip3
IMAGE_NAME := quay.io/yannick_siewe/k8s-iam-operator
IMAGE_TAG := dev
HELM_CHART := charts/k8s-iam-operator

# Colors for output
CYAN := \033[36m
GREEN := \033[32m
RESET := \033[0m

help: ## Show this help
	@echo "$(CYAN)k8s-iam-operator$(RESET) - Kubernetes IAM Operator"
	@echo ""
	@echo "$(GREEN)Available targets:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2}'

install-deps: ## Install Python dependencies
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-cov pytest-mock flake8 mypy types-requests

lint: ## Run linting (flake8 and mypy)
	@echo "$(CYAN)Running flake8...$(RESET)"
	flake8 app/ tests/ --count --show-source --statistics
	@echo "$(CYAN)Running mypy...$(RESET)"
	mypy app/ --ignore-missing-imports || true
	@echo "$(GREEN)Linting complete!$(RESET)"

test: ## Run unit tests
	@echo "$(CYAN)Running unit tests...$(RESET)"
	pytest tests/unit/ -v
	@echo "$(GREEN)Tests complete!$(RESET)"

test-coverage: ## Run unit tests with coverage report
	@echo "$(CYAN)Running unit tests with coverage...$(RESET)"
	pytest tests/unit/ -v --cov=app --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)Coverage report generated in htmlcov/$(RESET)"

integration-test: ## Run integration tests (requires Kubernetes cluster)
	@echo "$(CYAN)Running integration tests...$(RESET)"
	pytest tests/integration/ -v --timeout=300
	@echo "$(GREEN)Integration tests complete!$(RESET)"

build: ## Build Docker image
	@echo "$(CYAN)Building Docker image...$(RESET)"
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .
	@echo "$(GREEN)Image built: $(IMAGE_NAME):$(IMAGE_TAG)$(RESET)"

build-alpine: ## Build Alpine-based Docker image
	@echo "$(CYAN)Building Alpine Docker image...$(RESET)"
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG)-alpine .
	@echo "$(GREEN)Image built: $(IMAGE_NAME):$(IMAGE_TAG)-alpine$(RESET)"

push: ## Push Docker image to registry
	@echo "$(CYAN)Pushing Docker image...$(RESET)"
	docker push $(IMAGE_NAME):$(IMAGE_TAG)
	@echo "$(GREEN)Image pushed!$(RESET)"

run: ## Run operator locally
	@echo "$(CYAN)Starting operator locally...$(RESET)"
	$(PYTHON) -m app

run-dev: ## Run operator with debug logging
	@echo "$(CYAN)Starting operator in dev mode...$(RESET)"
	LOG_LEVEL=DEBUG $(PYTHON) -m app

helm-lint: ## Lint Helm chart
	@echo "$(CYAN)Linting Helm chart...$(RESET)"
	helm lint $(HELM_CHART)
	@echo "$(GREEN)Helm lint complete!$(RESET)"

helm-template: ## Render Helm chart templates
	@echo "$(CYAN)Rendering Helm templates...$(RESET)"
	helm template k8s-iam-operator $(HELM_CHART) --debug

helm-install: ## Install Helm chart to current cluster
	@echo "$(CYAN)Installing Helm chart...$(RESET)"
	helm upgrade --install k8s-iam-operator $(HELM_CHART) \
		--namespace iam \
		--create-namespace
	@echo "$(GREEN)Helm chart installed!$(RESET)"

helm-uninstall: ## Uninstall Helm chart
	@echo "$(CYAN)Uninstalling Helm chart...$(RESET)"
	helm uninstall k8s-iam-operator --namespace iam || true
	@echo "$(GREEN)Helm chart uninstalled!$(RESET)"

clean: ## Clean up generated files
	@echo "$(CYAN)Cleaning up...$(RESET)"
	rm -rf __pycache__ .pytest_cache htmlcov .coverage coverage.xml
	rm -rf app/__pycache__ tests/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete!$(RESET)"

kind-create: ## Create kind cluster for testing
	@echo "$(CYAN)Creating kind cluster...$(RESET)"
	kind create cluster --name iam-test
	@echo "$(GREEN)Kind cluster created!$(RESET)"

kind-delete: ## Delete kind cluster
	@echo "$(CYAN)Deleting kind cluster...$(RESET)"
	kind delete cluster --name iam-test
	@echo "$(GREEN)Kind cluster deleted!$(RESET)"

kind-load: build ## Load image into kind cluster
	@echo "$(CYAN)Loading image into kind...$(RESET)"
	kind load docker-image $(IMAGE_NAME):$(IMAGE_TAG) --name iam-test
	@echo "$(GREEN)Image loaded!$(RESET)"

crds-install: ## Install CRDs to cluster
	@echo "$(CYAN)Installing CRDs...$(RESET)"
	kubectl apply -f crd/
	@echo "$(GREEN)CRDs installed!$(RESET)"

crds-uninstall: ## Uninstall CRDs from cluster
	@echo "$(CYAN)Uninstalling CRDs...$(RESET)"
	kubectl delete -f crd/ || true
	@echo "$(GREEN)CRDs uninstalled!$(RESET)"
