PYTHON       := /usr/bin/env python3
VERSION_FILE := ./src/dug/_version.py
VERSION      := $(shell cut -d " " -f 3 ${VERSION_FILE})
DOCKER_TAG   := dug-make-test:${VERSION}

.PHONY: clean install test build image reinstall

all: clean install test build image

clean:
	rm -rf build
	rm -rf dist
	rm -rf src/dug.egg-info
	${PYTHON} -m pip uninstall -y dug
	${PYTHON} -m pip uninstall -y -r requirements.txt

install:
	${PYTHON} -m pip install --upgrade pip
	${PYTHON} -m pip install -r requirements.txt
	${PYTHON} -m pip install .

reinstall: clean install

test:
	# TODO spin up docker-compose backend for integration tests?
	${PYTHON} -m pytest --doctest-modules src
	${PYTHON} -m pytest tests/unit

build:
	echo "Building distribution packages for version $(VERSION)"
	${PYTHON} -m pip install --upgrade build
	${PYTHON} -m build --sdist --wheel .

image:
	echo "Building docker image: $(DOCKER_TAG)"
	docker build -t ${DOCKER_TAG} -f Dockerfile .