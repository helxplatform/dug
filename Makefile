PYTHON       = $(shell which python3)
VERSION_FILE = ./src/dug/_version.py
VERSION      = $(shell cut -d " " -f 3 ${VERSION_FILE})
DOCKER_REPO  = docker.io
DOCKER_OWNER = rti
DOCKER_APP	 = dug
DOCKER_TAG   = ${VERSION}
DOCKER_IMAGE = ${DOCKER_OWNER}/${DOCKER_APP}:$(DOCKER_TAG)
export PYTHONPATH = $(shell echo ${PWD})/src

.DEFAULT_GOAL = help

.PHONY: help clean install test build image publish

#help: List available tasks on this project
help:
	@grep -E '^#[a-zA-Z\.\-]+:.*$$' $(MAKEFILE_LIST) | tr -d '#' | awk 'BEGIN {FS = ": "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

init:
	git --version
	echo "Please make sure your git version is greater than 2.9.0. If it's not, this command will fail."
	git config --local core.hooksPath .githooks/

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

#install.dug: Install dug as a library to the current Python environment.
install.dug:
	${PYTHON} -m pip install .

#test: Run all tests
test:
	# ${PYTHON} -m flake8 src
	${PYTHON} -m pytest --doctest-modules src
	coverage run -m pytest tests

coverage:
	coverage report

#build: Build Docker image
build:
	echo "Building docker image: ${DOCKER_IMAGE}"
	docker build -t ${DOCKER_IMAGE} -f Dockerfile .
	echo "Successfully built: ${DOCKER_IMAGE}"

#publish: Build and push docker image
publish: build
	docker tag ${DOCKER_IMAGE} ${DOCKER_REPO}/${DOCKER_IMAGE}
	docker push ${DOCKER_REPO}/${DOCKER_IMAGE}
