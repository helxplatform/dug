PYTHON       := /usr/bin/env python3
VERSION_FILE := ./src/dug/_version.py
VERSION      := $(shell cut -d " " -f 3 ${VERSION_FILE})

.PHONY: install clean test build image stack publish

clean:
	rm -rf build
	rm -rf dist
	rm -rf src/dug.egg-info
	${PYTHON} -m pip uninstall -y dug
	${PYTHON} -m pip uninstall -y -r requirements.txt

install:
	${PYTHON} -m pip install --upgrade pip
	${PYTHON} -m pip install -r requirements.txt
	${PYTHON} -m pip install -e .

reinstall: clean install

test:
	# TODO spin up docker-compose backend for integration tests?
	${PYTHON} -m pytest tests/unit

build: reinstall test
	${PYTHON} -m pip install --upgrade build
	${PYTHON} -m build --sdist --wheel .

image: reinstall test
	docker build -t dug-make-test:${VERSION} -f Dockerfile .

stack:
	docker-compose up api