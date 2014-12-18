SHELL := /bin/bash
TOX_DIR := .tox
VIRTUALENV_DIR ?= virtualenv

# Sphinx docs options
SPHINXBUILD := sphinx-build
DOC_SOURCE_DIR := docs/source
DOC_BUILD_DIR := docs/build

BINARIES := bin

# All components are prefixed by st2
COMPONENTS := $(wildcard st2*)

# Components that implement a component-controlled test-runner. These components provide an
# in-component Makefile. (Temporary fix until I can generalize the pecan unittest setup. -mar)
COMPONENT_SPECIFIC_TESTS := st2tests st2synapse

# nasty hack to get a space into a variable
space_char :=
space_char +=
COMPONENT_PYTHONPATH = $(subst $(space_char),:,$(realpath $(COMPONENTS)))
COMPONENTS_TEST := $(foreach component,$(filter-out $(COMPONENT_SPECIFIC_TESTS),$(COMPONENTS)),$(component))

PYTHON_TARGET := 2.7

REQUIREMENTS := requirements.txt test-requirements.txt st2synapse/requirements.txt st2client/requirements.txt

.PHONY: all
all: requirements check tests docs

# Target for debugging Makefile variable assembly
.PHONY: play
play:
	@echo COMPONENTS=$(COMPONENTS)
	@echo COMPONENTS_TEST=$(COMPONENTS_TEST)
	@echo COMPONENT_PYTHONPATH=$(COMPONENT_PYTHONPATH)


.PHONY: check
check: requirements flake8 checklogs

.PHONY: checklogs
checklogs:
	@echo
	@echo "================== LOG WATCHER ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; ./tools/log_watcher.py 10

.PHONY: docs
docs: requirements .docs

.PHONY: .docs
.docs:
	@echo
	@echo "====================docs===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; $(SPHINXBUILD) -W -b html $(DOC_SOURCE_DIR) $(DOC_BUILD_DIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(DOC_BUILD_DIR)/html."

.PHONY: livedocs
livedocs: docs .livedocs

.PHONY: .livedocs
.livedocs:
	@echo
	@echo "==========================================================="
	@echo "                       RUNNING DOCS"
	@echo "==========================================================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; sphinx-autobuild -H 0.0.0.0 -b html $(DOC_SOURCE_DIR) $(DOC_BUILD_DIR)/html
	@echo

.PHONY: pylint
pylint: requirements .pylint

.PHONY: .pylint
.pylint:
	@echo
	@echo "================== pylint ===================="
	@echo
	@for component in $(COMPONENTS); do\
		echo "==========================================================="; \
		echo "Running pylint on" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate; pylint -E --rcfile=./.pylintrc $$component/$$component; \
	done

.PHONY: flake8
flake8: requirements .flake8

.PHONY: .flake8
.flake8:
	@echo
	@echo "==================== flake ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./.flake8 $(COMPONENTS)

.PHONY: lint
lint: requirements .flake8 .pylint

.PHONY: clean
clean: .cleanpycs .cleandocs

.PHONY: .cleanpycs
.cleanpycs:
	@echo "Removing all .pyc files"
	find $(COMPONENTS)  -name \*.pyc -type f -print0 | xargs -0 -I {} rm {}

.PHONY: .cleandocs
.cleandocs:
	@echo "Removing generated documentation"
	rm -rf $(DOC_BUILD_DIR)

.PHONY: distclean
distclean: clean
	@echo
	@echo "==================== distclean ===================="
	@echo
	rm -rf $(VIRTUALENV_DIR)

.PHONY: requirements
requirements: virtualenv $(REQUIREMENTS)
	@echo
	@echo "==================== requirements ===================="
	@echo
	for req in $(REQUIREMENTS); do \
		echo "Installing $$req..." ; \
		. $(VIRTUALENV_DIR)/bin/activate && pip install -U -q -r $$req ; \
	done

.PHONY: virtualenv
virtualenv: $(VIRTUALENV_DIR)/bin/activate
$(VIRTUALENV_DIR)/bin/activate:
	@echo
	@echo "==================== virtualenv ===================="
	@echo
	test -d $(VIRTUALENV_DIR) || virtualenv --no-site-packages $(VIRTUALENV_DIR)

	# Setup PYTHONPATH in bash activate script...
	echo '' >> $(VIRTUALENV_DIR)/bin/activate
	echo '_OLD_PYTHONPATH=$$PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate
	echo 'PYTHONPATH=$$_OLD_PYTHONPATH:$(COMPONENT_PYTHONPATH)' >> $(VIRTUALENV_DIR)/bin/activate
	echo 'export PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate
	touch $(VIRTUALENV_DIR)/bin/activate

	# Setup PYTHONPATH in fish activate script...
	echo '' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo 'set -gx _OLD_PYTHONPATH $$PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo 'set -gx PYTHONPATH $$_OLD_PYTHONPATH $(COMPONENT_PYTHONPATH)' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo 'functions -c deactivate old_deactivate' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo 'function deactivate' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo '  if test -n $$_OLD_PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo '    set -gx PYTHONPATH $$_OLD_PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo '    set -e _OLD_PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo '  end' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo '  old_deactivate' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo '  functions -e old_deactivate' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo 'end' >> $(VIRTUALENV_DIR)/bin/activate.fish
	touch $(VIRTUALENV_DIR)/bin/activate.fish

.PHONY: tests
tests: pytests

.PHONY: pytests
pytests: requirements .flake8 .pytests-coverage

.PHONY: .pytests
.pytests: clean
	@echo
	@echo "==================== tests ===================="
	@echo "Affected components: $(COMPONENTS_TEST)"
	@echo
	@echo "----- Dropping st2-test db -----"
	@mongo st2-test --eval "db.dropDatabase();"
	@for component in $(COMPONENTS_TEST); do\
		echo "==========================================================="; \
		echo "Running tests in" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate; nosetests -s -v $$component/tests || exit 1; \
	done

.PHONY: .pytests-coverage
.pytests-coverage: clean
	@echo
	@echo "==================== tests with coverage ===================="
	@echo "Affected components: $(COMPONENTS_TEST)"
	@echo
	@for component in $(COMPONENTS_TEST); do\
		echo "==========================================================="; \
		echo "Running tests in" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate; nosetests -sv --with-xcoverage --xcoverage-file=coverage-$$component.xml --cover-package=$$component $$component/tests || exit 1; \
	done

.PHONY: itests
itests: requirements .pytests-integration

.PHONY: .pytests-integration
.pytests-integration: clean
	@echo
	@echo "==================== integration tests ===================="
	@echo
	@echo "===========================================================";
	@echo "Running tests in st2synapse";
	@echo "===========================================================";
	. $(VIRTUALENV_DIR)/bin/activate; nosetests -sv --with-xcoverage --xcoverage-file=coverage-st2synapse.xml --cover-package=st2synapse st2synapse/tests || exit 1;

.PHONY: rpms
rpms:
	@echo
	@echo "==================== rpm ===================="
	@echo
	rm -Rf ~/rpmbuild
	$(foreach COM,$(COMPONENTS), pushd $(COM); make rpm; popd;)
	pushd st2client && make rpm && popd

.PHONY: debs
debs:
	@echo
	@echo "==================== deb ===================="
	@echo
	rm -Rf ~/debbuild
	$(foreach COM,$(COMPONENTS), pushd $(COM); make deb; popd;)
	pushd st2client && make deb && popd
