PYTHON_FILES = $(shell find . -name '*.py' -not -path  './.direnv/*')

.PHONY: style
style:
	yapf -i $(PYTHON_FILES)

.PHONY: lint
lint: .pylintrc
	pylint $(PYTHON_FILES)

.PHONY: pylintrc
pylintrc: .pylintrc
.pylintrc:
	pylint --generate-rcfile > .pylintrc
	sed -i 's@#init-hook=@init-hook='\''import sys; sys.path.append("stubs/stm32")'\'@ .pylintrc

# Install any required python tools and modules
.PHONY: requirements
requirements:
	python3 -m pip install --upgrade pip
	pip3 install -r requirements.txt

# Run unittests on the host machine
.PHONY: tests
tests:
	pytest -vv

# Run unittests on the pyboard
.PHONY: tests-on-pyboard
tests-on-pyboard:
	rm -rf bioloid/__pycache__ tests/__pycache__
	rshell 'rsync upy /flash; rsync bioloid /flash/bioloid; rsync tests /flash/tests; cp run_tests.py /flash; repl ~ import run_tests'

# Do coverage analysis and print a report
.PHONY: coverage
coverage:
	coverage run --source=bioloid -m pytest
	coverage report -m
