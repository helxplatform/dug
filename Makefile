PYTHON       := /usr/bin/env python3
VERSION_FILE := ./src/dug/_version.py
VERSION      := $(shell cut -d " " -f 3 ${VERSION_FILE})

.PHONY: clean install test build image

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

test:
	# TODO spin up docker-compose backend for integration tests?
	${PYTHON} -m pytest tests/unit

build:
	${PYTHON} -m pip install --upgrade build
	${PYTHON} -m build --sdist --wheel .

image:
	docker build -t dug-make-test:${VERSION} -f Dockerfile .