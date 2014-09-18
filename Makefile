SHELL := /bin/bash
TOX_DIR := .tox
VIRTUALENV_DIR ?= virtualenv
WEB_DIR := web
STORMBOT_DIR := stormbot

DOXYGEN_CONFIG := Doxyfile
DOC_DIR := docs

BINARIES := bin

# All components are prefixed by st2
COMPONENTS := $(wildcard st2*)

# Components that implement a component-controlled test-runner. These components provide an
# in-component Makefile. (Temporary fix until I can generalize the pecan unittest setup. -mar)
COMPONENT_SPECIFIC_TESTS := st2tests

# nasty hack to get a space into a variable
space_char :=
space_char +=
COMPONENT_PYTHONPATH = $(subst $(space_char),:,$(realpath $(COMPONENTS)))
COMPONENTS_TEST := $(foreach component,$(filter-out $(COMPONENT_SPECIFIC_TESTS),$(COMPONENTS)),$(component))

PYTHON_TARGET := 2.7

REQUIREMENTS := requirements.txt test-requirements.txt

.PHONY: all
all: requirements web stormbot check tests

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
	@echo "==================LOG WATCHER===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; ./tools/log_watcher.py 10

.PHONY: docs
docs:
	@echo
	@echo "====================docs===================="
	@echo
	doxygen $(DOXYGEN_CONFIG)

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
	@echo "====================flake===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./.flake8 $(COMPONENTS)

.PHONY: clean
clean:
	@echo
	@echo "====================clean===================="
	@echo
	@echo "Removing all .pyc files"
	find $(COMPONENTS)  -name \*.pyc -type f -print0 | xargs -0 -I {} rm {}
	@echo "Removing generated documentation"
	rm -rf $(DOC_DIR)/html $(DOC_DIR)/latex $(DOC_DIR)/rtf

.PHONY: distclean
distclean: clean
	@echo
	@echo "====================distclean===================="
	@echo
	rm -rf $(VIRTUALENV_DIR)
	rm -rf $(WEB_DIR)/css/ $(WEB_DIR)/components/ $(WEB_DIR)/node_modules/ $(WEB_DIR)/font/
	rm -rf $(STORMBOT_DIR)/node_modules/

.PHONY: requirements
requirements: virtualenv $(REQUIREMENTS)
	@echo
	@echo "====================requirements===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate && pip install -U $(foreach req,$(REQUIREMENTS),-r $(req))

.PHONY: virtualenv
virtualenv: $(VIRTUALENV_DIR)/bin/activate
$(VIRTUALENV_DIR)/bin/activate:
	@echo
	@echo "====================virtualenv===================="
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

.PHONY: web
web:
	@echo
	@echo "====================web===================="
	@echo
	npm install --prefix $(WEB_DIR)
	bower install --config.cwd=$(WEB_DIR) --config.directory=components
	gulp --cwd $(WEB_DIR) build

.PHONY: botrqmnts
botrqmnts:
	npm install --prefix $(STORMBOT_DIR)

.PHONY: tests
tests: pytests bottests

.PHONY: pytests
pytests: requirements .flake8 .pytests-coverage

.PHONY: .pytests
.pytests:
	@echo
	@echo "====================tests===================="
	@echo
	@for component in $(COMPONENTS_TEST); do\
		echo "==========================================================="; \
		echo "Running tests in" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate; nosetests -s -v $$component/tests || exit 1; \
	done

.PHONY: .pytests-coverage
.pytests-coverage:
	@echo
	@echo "====================tests with coverage===================="
	@echo
	@for component in $(COMPONENTS_TEST); do\
		echo "==========================================================="; \
		echo "Running tests in" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate; nosetests -sv --with-xcoverage --xcoverage-file=coverage-$$component.xml --cover-package=$$component $$component/tests || exit 1; \
	done

.PHONY: bottests
bottests: botrqmnts
	npm test ../$(STORMBOT_DIR)

.PHONY: install
install:
	@echo
	@echo "====================install===================="
	@echo
	pip install -r requirements.txt
	cp -R st2*/st2* /usr/lib/python2.7/site-packages/
	mkdir -p /etc/stanley && cp conf/stanley.conf /etc/stanley/
	$(foreach COM,$(filter-out st2common,$(COMPONENTS)),mkdir -p /etc/$(COM) && cp $(COM)/conf/* /etc/$(COM)/ && cp $(COM)/bin/* /usr/bin/;)
	mkdir -p /etc/st2reactor/sensor/samples
	cp st2reactor/st2reactor/sensor/samples/* /etc/st2reactor/sensor/samples/

.PHONY: rpms
rpms:
	@echo
	@echo "====================rpm===================="
	@echo
	rm -Rf ~/rpmbuild
	$(foreach COM,$(COMPONENTS), pushd $(COM); make rpm; popd;)
	pushd st2client && make rpm && popd

.PHONY: debs
debs:
	@echo
	@echo "====================deb===================="
	@echo
	rm -Rf ~/debbuild
	$(foreach COM,$(COMPONENTS), pushd $(COM); make deb; popd;)
	pushd st2client && make deb && popd
