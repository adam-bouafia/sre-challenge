.PHONY: test build vm-up vm-down kind-up deploy monitoring clean

CONTAINER_ENGINE ?= $(shell command -v podman 2>/dev/null || echo docker)
IMAGE_REPO ?= ecorp
IMAGE_TAG  ?= dev
IMAGE      := $(IMAGE_REPO):$(IMAGE_TAG)
KIND_CLUSTER ?= ecorp
NAMESPACE ?= ecorp
INGRESS_TAG ?= controller-v1.11.3
CALICO_VERSION ?= v3.28.0

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
# we turn it off and install calico, else the chart's NetworkPolicy is a no-op
kind-up:
	kind create cluster --name $(KIND_CLUSTER) --config k8s/kind-config.yaml
	kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/$(CALICO_VERSION)/manifests/calico.yaml
	kubectl wait --for=condition=Ready nodes --all --timeout=180s
	kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/$(INGRESS_TAG)/deploy/static/provider/kind/deploy.yaml
	kubectl wait --namespace ingress-nginx --for=condition=Ready pod \
		--selector=app.kubernetes.io/component=controller --timeout=180s

# PVC wont bind without a StorageClass. if the cluster has none already, we install the local-path-provisioner:
#   kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml
deploy: build
	kind load docker-image $(IMAGE) --name $(KIND_CLUSTER) 2>/dev/null || true
	helm upgrade --install ecorp charts/ecorp \
		--namespace $(NAMESPACE) --create-namespace \
		--set image.repository=$(IMAGE_REPO) \
		--set image.tag=$(IMAGE_TAG) \
		--set image.pullPolicy=IfNotPresent

# goes into the "monitoring" namespace. on a shared cluster , check what is already there first
monitoring:
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
	helm repo update prometheus-community
	helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
		--namespace monitoring --create-namespace \
		-f k8s/monitoring-values.yaml

clean:
	-helm uninstall ecorp --namespace $(NAMESPACE)
	-kind delete cluster --name $(KIND_CLUSTER)
	-cd vm && vagrant destroy -f
