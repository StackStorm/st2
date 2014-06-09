REPO_ROOT := ..
VIRTUALENV_DIR=virtualenv

COMPONENTS := st2actioncontroller

PEP8_CONFIG := $(REPO_ROOT)/.pep8
FLAKE8_CONFIG := $(REPO_ROOT)/.flake8

.PHONY: clean
clean:
	rm -rf *.egg-info
	rm -rf build
	find . -name \*.pyc -type f -delete
	find . -name \*.pyo -type f -delete

.PHONY: test
test:
	. ../$(VIRTUALENV_DIR)/bin/activate; PECAN_CONFIG=tests/config.py python setup.py test -q

.PHONY: pep8
pep8:
	pep8 --config $(PEP8_CONFIG) $(COMPONENTS)

.PHONY: flake8
flake8:
	flake8 --config $(FLAKE8_CONFIG) $(COMPONENTS)
