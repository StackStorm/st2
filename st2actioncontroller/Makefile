REPO_ROOT := ..
VIRTUALENV_DIR=virtualenv

.PHONY: clean
clean:
	rm -rf *.egg-info
	rm -rf build
	find . -name \*.pyc -type f -delete
	find . -name \*.pyo -type f -delete

.PHONY: test
test:
	. ../$(VIRTUALENV_DIR)/bin/activate; PECAN_CONFIG=tests/config.py python setup.py test -q
