PYTHON       := /usr/bin/env python3
VERSION_FILE := ./src/dug/_version.py
VERSION      := $(shell cat ${VERSION_FILE} | cut -d " " -f 3)

.PHONY: install clean test build image stack publish

install:
	# TODO should this install local directory or build then install?
	${PYTHON} -m pip install --upgrade pip
	${PYTHON} -m pip install -r requirements.txt
	${PYTHON} -m pip install -e .

clean:
	rm -rf build
	rm -rf dist

test:
	echo $(VERSION)
	${PYTHON} -m pytest .

build: test
	${PYTHON} -m pip install --upgrade build
	${PYTHON} -m build --sdist --wheel .

image: test
	docker build -t dug-make-test:${VERSION} -f Dockerfile .

stack:
	docker-compose up api