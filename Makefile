PYTHON       := /usr/bin/env python3
VERSION_FILE := ./src/dug/_version.py
VERSION      := $(shell cat ${VERSION_FILE} | cut -d " " -f 3)

.PHONY: install clean test build image stack publish

clean:
	rm -rf build
	rm -rf dist
	${PYTHON} -m pip uninstall -y dug
	${PYTHON} -m pip uninstall -y -r requirements.txt

install:
	${PYTHON} -m pip install --upgrade pip
	${PYTHON} -m pip install -r requirements.txt
	${PYTHON} -m pip install -e .

test:
	# TODO spin up docker-compose backend for integration tests?
	${PYTHON} -m pytest tests/unit

build: clean install test
	${PYTHON} -m pip install --upgrade build
	${PYTHON} -m build --sdist --wheel .

image: clean install test
	docker build -t dug-make-test:${VERSION} -f Dockerfile .

stack:
	docker-compose up api