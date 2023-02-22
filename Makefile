BUILDS := $(patsubst apps/%/,%, $(dir $(wildcard apps/*/Dockerfile)))
#DOCKER_REPO_URL := k3d-registry.localhost:39727

APP_NAME = $*
APP_VERSION = $(shell cat apps/$*/VERSION)

build-%:
	@echo "***********************************"
	@echo "Building ${APP_NAME}:${APP_VERSION}"
	DOCKER_BUILDKIT=1 docker build -t $*:${APP_VERSION} --force-rm apps/${APP_NAME}

push-%: build-%
	@echo "**********************************"
	@echo "Pushing ${APP_NAME}:${APP_VERSION}"
	docker tag $*:${APP_VERSION} $(DOCKER_REPO_URL)/$*:${APP_VERSION}
	docker push $(DOCKER_REPO_URL)/$*:${APP_VERSION}

deploy-%: push-%
	@echo "************************************"
	@echo "Deploying ${APP_NAME}:${APP_VERSION}"
	kubectl apply -f apps/${APP_NAME}/*.yaml


build: $(addprefix build-,$(BUILDS))
push: $(addprefix push-,$(BUILDS))
deploy: $(addprefix deploy-,$(BUILDS))
all: build push deploy
.PHONY: all build push deploy
