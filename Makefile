# Docker Multi-Architecture Build Makefile
#
# Usage:
#   make build-nc         # Build and push noc-claude
#   make build-monitor    # Build and push ping-monitor
#   make build-frontend   # Build and push frontend
#   make build-all        # Build and push all
#   make build-nc-local   # Build for local arch only (no push)

PLATFORMS := linux/amd64,linux/arm64
NC_IMAGE := taylor01/noc-claude:latest
MONITOR_IMAGE := taylor01/ping-monitor:latest
FRONTEND_IMAGE := taylor01/ping-monitor-frontend:latest

.PHONY: build-nc build-monitor build-frontend build-all build-nc-local build-monitor-local build-frontend-local

# Ensure buildx builder exists
setup-buildx:
	@docker buildx inspect multiarch > /dev/null 2>&1 || \
		docker buildx create --name multiarch --use

# Build and push noc-claude for multiple architectures
build-nc: setup-buildx
	docker buildx build \
		--platform $(PLATFORMS) \
		-t $(NC_IMAGE) \
		--push \
		noc_claude/

# Build and push ping-monitor for multiple architectures
build-monitor: setup-buildx
	docker buildx build \
		--platform $(PLATFORMS) \
		-t $(MONITOR_IMAGE) \
		--push \
		monitor/

# Build and push frontend for multiple architectures
build-frontend: setup-buildx
	docker buildx build \
		--platform $(PLATFORMS) \
		-t $(FRONTEND_IMAGE) \
		--push \
		frontend/

# Build and push all images
build-all: build-nc build-monitor build-frontend

# Local builds (current architecture only, loads into docker)
build-nc-local:
	docker build -t $(NC_IMAGE) noc_claude/

build-monitor-local:
	docker build -t $(MONITOR_IMAGE) monitor/

build-frontend-local:
	docker build -t $(FRONTEND_IMAGE) frontend/
