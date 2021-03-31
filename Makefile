PYTHON       := /usr/bin/env python3
VERSION_FILE := ./src/dug/_version.py
VERSION      := $(shell cut -d " " -f 3 ${VERSION_FILE})
DOCKER_TAG   := dug-make-test:${VERSION}

.DEFAULT_GOAL := help

.PHONY: help clean install test build image

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

#test.lint: Run flake8 on the source code
test.lint:
	${PYTHON} -m flake8 src

#test.doc: Run doctests in the source code
test.doc:
	${PYTHON} -m pytest --doctest-modules src

#test.unit: Run unit tests
test.unit:
	${PYTHON} -m pytest tests/unit

#test: Run all tests
test: test.doc test.unit

#build: Build wheel and source distribution packages
build:
	echo "Building distribution packages for version $(VERSION)"
	${PYTHON} -m pip install --upgrade build
	${PYTHON} -m build --sdist --wheel .

#image: Build Docker image
image:
	echo "Building docker image: $(DOCKER_TAG)"
	docker build -t ${DOCKER_TAG} -f Dockerfile .

#all: Alias to clean, install, test, build, and image
all: clean install test build image
