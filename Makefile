PYTHON = /usr/bin/env python3
VERSION = test

install:
	${PYTHON} -m pip install --upgrade pip
	${PYTHON} -m pip install -r requirements.txt
	${PYTHON} -m pip install -e .

clean:
	rm -rf build
	rm -rf dist

package: clean
	${PYTHON} -m pip install --upgrade build
	${PYTHON} -m build --sdist --wheel .

test:
	${PYTHON} -m pytest .

image:
	# TODO get version from src/dug/_version.py
	docker build -t dug-make-test:${VERSION} -f Dockerfile .

stack:
	docker-compose up api