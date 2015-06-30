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
COMPONENT_SPECIFIC_TESTS := st2tests

# nasty hack to get a space into a variable
space_char :=
space_char +=
COMPONENT_PYTHONPATH = $(subst $(space_char),:,$(realpath $(COMPONENTS)))
COMPONENTS_TEST := $(foreach component,$(filter-out $(COMPONENT_SPECIFIC_TESTS),$(COMPONENTS)),$(component))

PYTHON_TARGET := 2.7

REQUIREMENTS := requirements.txt test-requirements.txt

PIP_OPTIONS := $(ST2_PIP_OPTIONS)

ifndef PIP_OPTIONS
	PIP_OPTIONS := -U -q -r
endif

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
	. $(VIRTUALENV_DIR)/bin/activate; ./scripts/generate-runner-parameters-documentation.py
	. $(VIRTUALENV_DIR)/bin/activate; ./scripts/generate-internal-triggers-table.py
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
	# Lint st2 components
	@for component in $(COMPONENTS); do\
		echo "==========================================================="; \
		echo "Running pylint on" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate; pylint -E --rcfile=./.pylintrc --load-plugins=pylint_plugins.api_models $$component/$$component || exit 1; \
	done
	# Lint Python pack management actions
	. $(VIRTUALENV_DIR)/bin/activate; pylint -E --rcfile=./.pylintrc --load-plugins=pylint_plugins.api_models contrib/packs/actions/pack_mgmt/ || exit 1;
	# Lint Python scripts
	. $(VIRTUALENV_DIR)/bin/activate; pylint -E --rcfile=./.pylintrc --load-plugins=pylint_plugins.api_models scripts/*.py || exit 1;

.PHONY: flake8
flake8: requirements .flake8

.PHONY: .flake8
.flake8:
	@echo
	@echo "==================== flake ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./.flake8 $(COMPONENTS)
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./.flake8 contrib/packs/actions/pack_mgmt/
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./.flake8 scripts/

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

.PHONY: .cleanmongodb
.cleanmongodb:
	@echo "==================== cleanmongodb ===================="
	@echo "----- Dropping all MongoDB databases -----"
	@sudo pkill -9 mongod
	@sudo rm -rf /var/lib/mongodb/*
	@sudo chown -R mongodb:mongodb /var/lib/mongodb/
	@sudo service mongodb start
	@sleep 1
	@mongo --eval "rs.initiate()"
	@sleep 5

.PHONY: .cleanmysql
.cleanmysql:
	@echo "==================== cleanmysql ===================="
	@echo "----- Dropping all Mistral MYSQL databases -----"
	@mysql -uroot -pStackStorm -e "DROP DATABASE IF EXISTS mistral"
	@mysql -uroot -pStackStorm -e "CREATE DATABASE mistral"
	@mysql -uroot -pStackStorm -e "GRANT ALL PRIVILEGES ON mistral.* TO 'mistral'@'localhost' IDENTIFIED BY 'StackStorm'"
	@mysql -uroot -pStackStorm -e "FLUSH PRIVILEGES"
	@/opt/openstack/mistral/.venv/bin/python /opt/openstack/mistral/tools/sync_db.py --config-file /etc/mistral/mistral.conf

.PHONY: .cleanrabbitmq
.cleanrabbitmq:
	@echo "==================== cleanrabbitmq ===================="
	@echo "Deleting all RabbitMQ queue and exchanges"
	@sudo rabbitmqctl stop_app
	@sudo rabbitmqctl reset
	@sudo rabbitmqctl start_app

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
	# Merge into one st2 components-wide requirements.txt file.
	python ./scripts/fixate-requirements.py -s st2*/in-requirements.txt -f fixed-requirements.txt
	for req in $(REQUIREMENTS); do \
		echo "Installing $$req..." ; \
		. $(VIRTUALENV_DIR)/bin/activate && pip install $(PIP_OPTIONS) $$req ; \
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

# Travis cannot run itests since those require users to be configured etc.
# Creating special travis target. (Yuck!)
.PHONY: tests-travis
tests-travis: requirements unit-tests-coverage

.PHONY: pytests
pytests: requirements .flake8 .pylint .pytests-coverage

.PHONY: .pytests
.pytests: unit-tests itests clean

.PHONY: .pytests-coverage
.pytests-coverage: unit-tests-coverage itests clean

.PHONY: unit-tests
unit-tests:
	@echo
	@echo "==================== tests ===================="
	@echo
	@echo "----- Dropping st2-test db -----"
	@mongo st2-test --eval "db.dropDatabase();"
	@for component in $(COMPONENTS_TEST); do\
		echo "==========================================================="; \
		echo "Running tests in" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate; nosetests -s -v $$component/tests/unit || exit 1; \
	done

.PHONY: unit-tests-coverage
unit-tests-coverage:
	@echo
	@echo "==================== unit tests with coverage ===================="
	@echo
	@echo "----- Dropping st2-test db -----"
	@mongo st2-test --eval "db.dropDatabase();"
	@for component in $(COMPONENTS_TEST); do\
		echo "==========================================================="; \
		echo "Running tests in" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate; nosetests -sv --with-xcoverage --xcoverage-file=coverage-$$component.xml --cover-package=$$component $$component/tests/unit || exit 1; \
	done

.PHONY: itests
itests: requirements .itests

.PHONY: .itests
.itests:
	@echo
	@echo "==================== integration tests ===================="
	@echo
	@echo "----- Dropping st2-test db -----"
	@mongo st2-test --eval "db.dropDatabase();"
	@for component in $(COMPONENTS_TEST); do\
		echo "==========================================================="; \
		echo "Running tests in" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate; nosetests -sv $$component/tests/integration || exit 1; \
	done

.PHONY: mistral-itests
mistral-itests: requirements .mistral-itests

.PHONY: .mistral-itests
.mistral-itests:
	@echo
	@echo "==================== MISTRAL integration tests ===================="
	@echo "The tests assume both st2 and mistral are running on localhost."
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; nosetests -s -v st2tests/integration || exit 1;

.PHONY: rpms
rpms:
	@echo
	@echo "==================== rpm ===================="
	@echo
	rm -Rf ~/rpmbuild
	$(foreach COM,$(COMPONENTS), pushd $(COM); make rpm; popd;)
	pushd st2client && make rpm && popd

rhel-rpms:
	@echo
	@echo "==================== rpm ===================="
	@echo
	rm -Rf ~/rpmbuild
	$(foreach COM,$(COMPONENTS), pushd $(COM); make rhel-rpm; popd;)
	pushd st2client && make rhel-rpm && popd

.PHONY: debs
debs:
	@echo
	@echo "==================== deb ===================="
	@echo
	rm -Rf ~/debbuild
	$(foreach COM,$(COMPONENTS), pushd $(COM); make deb; popd;)
	pushd st2client && make deb && popd
