.PHONY: test build vm-up vm-down kind-up deploy deploy-ghcr monitoring ci-local clean

CONTAINER_ENGINE ?= $(shell command -v podman 2>/dev/null || echo docker)
IMAGE_REPO ?= ecorp
IMAGE_TAG  ?= dev
IMAGE      := $(IMAGE_REPO):$(IMAGE_TAG)
KIND_CLUSTER ?= ecorp
NAMESPACE ?= ecorp
INGRESS_TAG ?= controller-v1.11.3
CALICO_VERSION ?= v3.28.0
GHCR_IMAGE_REPO ?= ghcr.io/adam-bouafia/sre-challenge
GHCR_IMAGE_TAG  ?= latest

# kind calls `docker` directly, it has no idea CONTAINER_ENGINE exists. on a
# machine with no real dockerd (rootless podman only, like this one), kind
# needs to be told explicitly to use podman instead, and podman's socket has
# to actually be running first.
ifeq ($(notdir $(CONTAINER_ENGINE)),podman)
KIND_ENV := KIND_EXPERIMENTAL_PROVIDER=podman DOCKER_HOST=unix:///run/user/$(shell id -u)/podman/podman.sock
else
KIND_ENV :=
endif

test:
	cd app && \
	. .venv/bin/activate 2>/dev/null || python3 -m venv .venv && . .venv/bin/activate; \
	pip install -q -r requirements-dev.txt && \
	python -m pytest --cov=ecorp --cov-report=term-missing

build:
	cd app && $(CONTAINER_ENGINE) build -t $(IMAGE) .

# needs vagrant + ansible-core, and than
# ansible-galaxy collection install -r vm/ansible/requirements.yml
vm-up:
	cd vm && vagrant up
	@echo "App: https://localhost:8443"

vm-down:
	cd vm && vagrant halt

# local kind cluster for testers. kindnetd doesnt enforce NetworkPolicy so
# we turn it off and install calico, else the chart's NetworkPolicy is a no-op.
# needs the VM down first: kind-config.yaml and the VM both claim host port
# 8443.
kind-up:
ifeq ($(notdir $(CONTAINER_ENGINE)),podman)
	systemctl --user start podman.socket
endif
	$(KIND_ENV) kind create cluster --name $(KIND_CLUSTER) --config k8s/kind-config.yaml
	kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/$(CALICO_VERSION)/manifests/calico.yaml
	kubectl wait --for=condition=Ready nodes --all --timeout=180s
	kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/$(INGRESS_TAG)/deploy/static/provider/kind/deploy.yaml
	kubectl wait --namespace ingress-nginx --for=condition=Ready pod \
		--selector=app.kubernetes.io/component=controller --timeout=180s

# PVC wont bind without a StorageClass. if the cluster has none already, we install the local-path-provisioner:
#   kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml
deploy: build
	$(KIND_ENV) kind load docker-image $(IMAGE) --name $(KIND_CLUSTER) 2>/dev/null || true
	helm upgrade --install ecorp charts/ecorp \
		--namespace $(NAMESPACE) --create-namespace \
		--set image.repository=$(IMAGE_REPO) \
		--set image.tag=$(IMAGE_TAG) \
		--set image.pullPolicy=IfNotPresent

# for an existing cluster (kubeadm, bare metal - anything that isn't kind):
# no local build or image load, pulls the image CI already pushed to GHCR.
# needs a StorageClass present first (see README's "Pod stuck Pending" note)
# and, if the package is private, `kubectl create secret docker-registry`
# or a node-level GHCR login so the pull actually succeeds.
deploy-ghcr:
	helm upgrade --install ecorp charts/ecorp \
		--namespace $(NAMESPACE) --create-namespace \
		--set image.repository=$(GHCR_IMAGE_REPO) \
		--set image.tag=$(GHCR_IMAGE_TAG) \
		--set image.pullPolicy=Always

# goes into the "monitoring" namespace. on a shared cluster , check what is already there first
monitoring:
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
	helm repo update prometheus-community
	helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
		--namespace monitoring --create-namespace \
		-f k8s/monitoring-values.yaml


# runs the CI workflow locally with act (github.com/nektos/act), against
# the rootless podman socket - no push to GitHub needed to see it work.
# `make ci-local` alone runs lint+test+security (fast, no docker-in-docker).
# JOB=docker-build (or image-scan/helm-validate) runs a later stage; those
# need --privileged for nested docker and aren't run by default.
ci-local:
	systemctl --user start podman.socket
	DOCKER_HOST=unix:///run/user/$$(id -u)/podman/podman.sock \
		act -P ubuntu-latest=catthehacker/ubuntu:act-latest \
		$(if $(JOB),-j $(JOB),-j lint && \
		DOCKER_HOST=unix:///run/user/$$(id -u)/podman/podman.sock \
		act -P ubuntu-latest=catthehacker/ubuntu:act-latest -j test && \
		DOCKER_HOST=unix:///run/user/$$(id -u)/podman/podman.sock \
		act -P ubuntu-latest=catthehacker/ubuntu:act-latest -j security)

clean:
	-helm uninstall ecorp --namespace $(NAMESPACE)
	-$(KIND_ENV) kind delete cluster --name $(KIND_CLUSTER)
	-cd vm && vagrant destroy -f
