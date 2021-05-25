PYTHON          := /usr/bin/env python3
VERSION_FILE    := ./src/dug/_version.py
VERSION         := $(shell cut -d " " -f 3 ${VERSION_FILE})
DOCKER_REGISTRY := docker.io
DOCKER_OWNER    := helxplatform
DOCKER_APP	    := dug
DOCKER_TAG      := ${VERSION}
DOCKER_IMAGE    := ${DOCKER_OWNER}/${DOCKER_APP}:$(DOCKER_TAG)

.DEFAULT_GOAL = help

.PHONY: help clean install test build image publish

#help: List available tasks on this project
help:
	@grep -E '^#[a-zA-Z\.\-]+:.*$$' $(MAKEFILE_LIST) | tr -d '#' | awk 'BEGIN {FS = ": "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

#clean: Remove old build artifacts and installed packages
clean:
	rm -rf build
	rm -rf dist
	rm -rf src/dug.egg-info
	${PYTHON} -m pip uninstall -y dug
	${PYTHON} -m pip uninstall -y -r requirements.txt

#install: Install application along with required development packages
install:
	${PYTHON} -m pip install --upgrade pip
	${PYTHON} -m pip install -r requirements.txt
	${PYTHON} -m pip install .

#test: Run all tests
test:
	${PYTHON} -m pytest --doctest-modules src
	${PYTHON} -m pytest tests

#build: Build the Docker image
build:
	echo "Building docker image: ${DOCKER_IMAGE}"
	docker build -t ${DOCKER_IMAGE} -f Dockerfile .
	echo "Successfully built: ${DOCKER_IMAGE}"
	echo "Testing ${DOCKER_IMAGE}"
	docker run ${DOCKER_IMAGE} make test

#publish: Push the Docker image
publish: build
	docker tag ${DOCKER_IMAGE} ${DOCKER_REGISTRY}/${DOCKER_IMAGE}
	docker push ${DOCKER_REGISTRY}/${DOCKER_IMAGE}

#all: Alias to clean, install, test, build, and image
all: clean install test build
