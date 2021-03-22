PYTHON = python3

install:
	PYTHON -m pip install -r requirements.txt
	PYTHON -m pip install -e .

package:
	PYTHON -m pip install --upgrade build
	PYTHON -m build --sdist --wheel .

test:
	PYTHON -m pytest .
