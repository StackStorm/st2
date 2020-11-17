ROOT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
SHELL := /bin/bash
TOX_DIR := .tox
OS := $(shell uname)

# We separate the OSX X and Linux virtualenvs so we can run in a Docker
# container (st2devbox) while doing things on our host Mac machine
ifeq ($(OS),Darwin)
	VIRTUALENV_DIR ?= virtualenv-osx
	VIRTUALENV_ST2CLIENT_DIR ?= virtualenv-st2client-osx
	VIRTUALENV_COMPONENTS_DIR ?= virtualenv-components-osx
else
	VIRTUALENV_DIR ?= virtualenv
	VIRTUALENV_ST2CLIENT_DIR ?= virtualenv-st2client
	VIRTUALENV_COMPONENTS_DIR ?= virtualenv-components
endif

PYTHON_VERSION ?= $(shell if [ -z "`which python3.6`" ]; then echo "python2.7"; else echo "python3.6"; fi)

BINARIES := bin

# All components are prefixed by st2 and not .egg-info.
COMPONENTS := $(shell ls -a | grep ^st2 | grep -v .egg-info)
COMPONENTS_RUNNERS := $(wildcard contrib/runners/*)
MOCK_RUNNERS := $(wildcard st2common/tests/runners/*)
COMPONENTS_WITHOUT_ST2TESTS := $(shell ls -a | grep ^st2 | grep -v .egg-info | grep -v st2tests | grep -v st2exporter)

COMPONENTS_WITH_RUNNERS := $(COMPONENTS) $(COMPONENTS_RUNNERS)

COMPONENTS_TEST_DIRS := $(wildcard st2*/tests) $(wildcard contrib/runners/*/tests)

# Components that implement a component-controlled test-runner. These components provide an
# in-component Makefile. (Temporary fix until I can generalize the pecan unittest setup. -mar)
# Note: We also want to ignore egg-info dir created during build
COMPONENT_SPECIFIC_TESTS := st2tests st2client.egg-info

# nasty hack to get a space into a variable
colon := :
comma := ,
dot := .
slash := /
space_char :=
space_char +=
COMPONENT_PYTHONPATH = $(subst $(space_char),:,$(realpath $(COMPONENTS_WITH_RUNNERS)))
COMPONENTS_TEST := $(foreach component,$(filter-out $(COMPONENT_SPECIFIC_TESTS),$(COMPONENTS_WITH_RUNNERS)),$(component))
COMPONENTS_TEST_COMMA := $(subst $(slash),$(dot),$(subst $(space_char),$(comma),$(COMPONENTS_TEST)))
COMPONENTS_TEST_MODULES := $(subst $(slash),$(dot),$(COMPONENTS_TEST_DIRS))
COMPONENTS_TEST_MODULES_COMMA := $(subst $(space_char),$(comma),$(COMPONENTS_TEST_MODULES))

COVERAGE_GLOBS := .coverage.unit.* .coverage.integration.*
COVERAGE_GLOBS_QUOTED := $(foreach glob,$(COVERAGE_GLOBS),'$(glob)')

ifeq ($(PYTHON_VERSION),python2.7)
	REQUIREMENTS := test-requirements-py27.txt requirements.txt
else
	REQUIREMENTS := test-requirements.txt requirements.txt
endif

# Pin common pip version here across all the targets
# Note! Periodic maintenance pip upgrades are required to be up-to-date with the latest pip security fixes and updates
PIP_VERSION ?= 20.0.2
PIP_OPTIONS := $(ST2_PIP_OPTIONS)

ifndef PYLINT_CONCURRENCY
	PYLINT_CONCURRENCY := 1
endif

NOSE_OPTS := --rednose --immediate --with-parallel

ifndef NOSE_TIME
	NOSE_TIME := yes
endif

ifeq ($(NOSE_TIME),yes)
	NOSE_OPTS := --rednose --immediate --with-parallel --with-timer
	NOSE_WITH_TIMER := 1
endif

ifndef PIP_OPTIONS
	PIP_OPTIONS :=
endif

# NOTE: We only run coverage on master and version branches and not on pull requests since
# it has a big performance overhead and is very slow.
ifeq ($(ENABLE_COVERAGE),yes)
	NOSE_COVERAGE_FLAGS := --with-coverage --cover-branches --cover-erase
	NOSE_COVERAGE_PACKAGES := --cover-package=$(COMPONENTS_TEST_COMMA)
else
	INCLUDE_TESTS_IN_COVERAGE :=
endif

# If we aren't running test coverage, don't try to include tests in coverage
# results
ifdef INCLUDE_TESTS_IN_COVERAGE
	NOSE_COVERAGE_FLAGS += --cover-tests
	NOSE_COVERAGE_PACKAGES := $(NOSE_COVERAGE_PACKAGES),$(COMPONENTS_TEST_MODULES_COMMA)
endif

.PHONY: all
all: requirements configgen check tests

.PHONY: .coverage_globs
.coverage_globs:
	@for coverage_result in $$( \
		for coverage_glob in $(COVERAGE_GLOBS_QUOTED); do \
			compgen -G $${coverage_glob}; \
		done; \
	); do \
		echo $${coverage_result}; \
	done

# Target for debugging Makefile variable assembly
.PHONY: play
play:
	@echo PYTHON_VERSION=$(PYTHON_VERSION)
	@echo
	@echo COVERAGE_GLOBS=$(COVERAGE_GLOBS_QUOTED)
	@echo
	@echo COMPONENTS=$(COMPONENTS)
	@echo
	@echo COMPONENTS_WITH_RUNNERS=$(COMPONENTS_WITH_RUNNERS)
	@echo
	@echo COMPONENTS_TEST=$(COMPONENTS_TEST)
	@echo
	@echo COMPONENTS_TEST_COMMA=$(COMPONENTS_TEST_COMMA)
	@echo
	@echo COMPONENTS_TEST_DIRS=$(COMPONENTS_TEST_DIRS)
	@echo
	@echo COMPONENTS_TEST_MODULES=$(COMPONENTS_TEST_MODULES)
	@echo
	@echo COMPONENTS_TEST_MODULES_COMMA=$(COMPONENTS_TEST_MODULES_COMMA)
	@echo
	@echo COMPONENT_PYTHONPATH=$(COMPONENT_PYTHONPATH)
	@echo
	@echo TRAVIS_PULL_REQUEST=$(TRAVIS_PULL_REQUEST)
	@echo
	@echo TRAVIS_EVENT_TYPE=$(TRAVIS_EVENT_TYPE)
	@echo
	@echo NOSE_OPTS=$(NOSE_OPTS)
	@echo
	@echo ENABLE_COVERAGE=$(ENABLE_COVERAGE)
	@echo
	@echo NOSE_COVERAGE_FLAGS=$(NOSE_COVERAGE_FLAGS)
	@echo
	@echo NOSE_COVERAGE_PACKAGES=$(NOSE_COVERAGE_PACKAGES)
	@echo
	@echo INCLUDE_TESTS_IN_COVERAGE=$(INCLUDE_TESTS_IN_COVERAGE)
	@echo

.PHONY: check
check: check-requirements check-sdist-requirements flake8 checklogs

# NOTE: We pass --no-deps to the script so we don't install all the
# package dependencies which are already installed as part of "requirements"
# make targets. This speeds up the build
.PHONY: install-runners
install-runners:
	@echo ""
	@echo "================== INSTALL RUNNERS ===================="
	@echo ""
	@for component in $(COMPONENTS_RUNNERS); do \
		echo "==========================================================="; \
		echo "Installing runner:" $$component; \
		echo "==========================================================="; \
		(. $(VIRTUALENV_DIR)/bin/activate; cd $$component; python setup.py develop --no-deps); \
	done

.PHONY: install-mock-runners
install-mock-runners:
	@echo ""
	@echo "================== INSTALL MOCK RUNNERS ===================="
	@echo ""
	@for component in $(MOCK_RUNNERS); do \
		echo "==========================================================="; \
		echo "Installing mock runner:" $$component; \
		echo "==========================================================="; \
		(. $(VIRTUALENV_DIR)/bin/activate; cd $$component; python setup.py develop --no-deps); \
	done

.PHONY: check-requirements
.check-requirements:
	@echo
	@echo "============== CHECKING REQUIREMENTS =============="
	@echo
	# Update requirements and then make sure no files were changed
	git status -- *requirements.txt */*requirements.txt | grep -q "nothing to commit" || { \
		echo "It looks like you directly modified a requirements.txt file, an"; \
		echo "in-requirements.txt file, or fixed-requirements.txt without running:"; \
		echo ""; \
		echo "    make .requirements"; \
		echo ""; \
		echo "Please update all of the requirements.txt files by running that command"; \
		echo "and committing all of the changed files. You can quickly check the results"; \
		echo "with:"; \
		echo ""; \
		echo "    make .check-requirements"; \
		echo ""; \
		exit 1; \
	}
	@echo "All requirements files are up-to-date!"

.PHONY: check-requirements
check-requirements: .requirements .check-requirements

.PHONY: .check-sdist-requirements
.check-sdist-requirements:
	@echo
	@echo "============== CHECKING SDIST REQUIREMENTS =============="
	@echo
	# Update requirements and then make sure no files were changed
	git status -- */dist_utils.py contrib/runners/*/dist_utils.py | grep -q "nothing to commit" || { \
		echo "It looks like you directly modified a dist_utils.py, or the source "; \
		echo "scripts/dist_utils.py file without running:"; \
		echo ""; \
		echo "    make .sdist-requirements"; \
		echo ""; \
		echo "Please update all of the dist_utils.py files by running that command"; \
		echo "and committing all of the changed files. You can quickly check the results"; \
		echo "with:"; \
		echo ""; \
		echo "    make .check-sdist-requirements"; \
		echo ""; \
		exit 1; \
	}
	@echo "All dist_utils.py files are up-to-date!"

.PHONY: check-sdist-requirements
check-sdist-requirements: .sdist-requirements .check-sdist-requirements

.PHONY: check-python-packages
check-python-packages:
	# Make target which verifies all the components Python packages are valid
	@echo ""
	@echo "================== CHECK PYTHON PACKAGES ===================="
	@echo ""
	test -f $(VIRTUALENV_COMPONENTS_DIR)/bin/activate || virtualenv --python=$(PYTHON_VERSION) $(VIRTUALENV_COMPONENTS_DIR) --no-download --system-site-packages
	@for component in $(COMPONENTS_WITHOUT_ST2TESTS); do \
		echo "==========================================================="; \
		echo "Checking component:" $$component; \
		echo "==========================================================="; \
		(set -e; cd $$component; ../$(VIRTUALENV_COMPONENTS_DIR)/bin/python setup.py --version) || exit 1; \
	done

.PHONY: check-python-packages-nightly
check-python-packages-nightly:
	# NOTE: This is subset of check-python-packages target.
	# We run more extensive and slower tests as part of the nightly build to speed up PR builds
	@echo ""
	@echo "================== CHECK PYTHON PACKAGES ===================="
	@echo ""

	test -f $(VIRTUALENV_COMPONENTS_DIR)/bin/activate || virtualenv --python=$(PYTHON_VERSION) $(VIRTUALENV_COMPONENTS_DIR) --no-download
	@for component in $(COMPONENTS_WITHOUT_ST2TESTS); do \
		echo "==========================================================="; \
		echo "Checking component:" $$component; \
		echo "==========================================================="; \
		(set -e; cd $$component; ../$(VIRTUALENV_COMPONENTS_DIR)/bin/python setup.py --version) || exit 1; \
		(set -e; cd $$component; ../$(VIRTUALENV_COMPONENTS_DIR)/bin/python setup.py sdist bdist_wheel) || exit 1; \
		(set -e; cd $$component; ../$(VIRTUALENV_COMPONENTS_DIR)/bin/python setup.py develop --no-deps) || exit 1; \
		($(VIRTUALENV_COMPONENTS_DIR)/bin/python -c "import $$component") || exit 1; \
		(set -e; cd $$component; rm -rf dist/; rm -rf $$component.egg-info) || exit 1; \
	done

.PHONY: ci-checks-nightly
ci-checks-nightly: check-python-packages-nightly

.PHONY: checklogs
checklogs:
	@echo
	@echo "================== LOG WATCHER ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; python ./tools/log_watcher.py 10

.PHONY: pylint
pylint: requirements .pylint

.PHONY: configgen
configgen: requirements .configgen

.PHONY: .configgen
.configgen:
	@echo
	@echo "================== config gen ===================="
	@echo
	echo "# Sample config which contains all the available options which the corresponding descriptions" > conf/st2.conf.sample;
	echo "# Note: This file is automatically generated using tools/config_gen.py - DO NOT UPDATE MANUALLY" >> conf/st2.conf.sample
	echo "" >> conf/st2.conf.sample
	. $(VIRTUALENV_DIR)/bin/activate; python ./tools/config_gen.py >> conf/st2.conf.sample;

.PHONY: schemasgen
schemasgen: requirements .schemasgen

.PHONY: .schemasgen
.schemasgen:
	@echo
	@echo "================== content model schemas gen ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; python ./st2common/bin/st2-generate-schemas;

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
		. $(VIRTUALENV_DIR)/bin/activate ; pylint -j $(PYLINT_CONCURRENCY) -E --rcfile=./lint-configs/python/.pylintrc --load-plugins=pylint_plugins.api_models --load-plugins=pylint_plugins.db_models $$component/$$component || exit 1; \
	done
	# Lint runner modules and packages
	@for component in $(COMPONENTS_RUNNERS); do\
		echo "==========================================================="; \
		echo "Running pylint on" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate ; pylint -j $(PYLINT_CONCURRENCY) -E --rcfile=./lint-configs/python/.pylintrc --load-plugins=pylint_plugins.api_models --load-plugins=pylint_plugins.db_models $$component/*.py || exit 1; \
	done
	# Lint Python pack management actions
	. $(VIRTUALENV_DIR)/bin/activate; pylint -j $(PYLINT_CONCURRENCY) -E --rcfile=./lint-configs/python/.pylintrc --load-plugins=pylint_plugins.api_models contrib/packs/actions/*.py || exit 1;
	. $(VIRTUALENV_DIR)/bin/activate; pylint -j $(PYLINT_CONCURRENCY) -E --rcfile=./lint-configs/python/.pylintrc --load-plugins=pylint_plugins.api_models contrib/packs/actions/*/*.py || exit 1;
	# Lint other packs
	. $(VIRTUALENV_DIR)/bin/activate; pylint -j $(PYLINT_CONCURRENCY) -E --rcfile=./lint-configs/python/.pylintrc --load-plugins=pylint_plugins.api_models contrib/linux/*/*.py || exit 1;
	. $(VIRTUALENV_DIR)/bin/activate; pylint -j $(PYLINT_CONCURRENCY) -E --rcfile=./lint-configs/python/.pylintrc --load-plugins=pylint_plugins.api_models contrib/chatops/*/*.py || exit 1;
	# Lint Python scripts
	. $(VIRTUALENV_DIR)/bin/activate; pylint -j $(PYLINT_CONCURRENCY) -E --rcfile=./lint-configs/python/.pylintrc --load-plugins=pylint_plugins.api_models scripts/*.py || exit 1;
	. $(VIRTUALENV_DIR)/bin/activate; pylint -j $(PYLINT_CONCURRENCY) -E --rcfile=./lint-configs/python/.pylintrc --load-plugins=pylint_plugins.api_models tools/*.py || exit 1;
	. $(VIRTUALENV_DIR)/bin/activate; pylint -j $(PYLINT_CONCURRENCY) -E --rcfile=./lint-configs/python/.pylintrc pylint_plugins/*.py || exit 1;

.PHONY: lint-api-spec
lint-api-spec: requirements .lint-api-spec

.PHONY: .lint-api-spec
.lint-api-spec:
	@echo
	@echo "================== Lint API spec ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; python st2common/bin/st2-validate-api-spec --config-file conf/st2.dev.conf

.PHONY: generate-api-spec
generate-api-spec: requirements .generate-api-spec

.PHONY: .generate-api-spec
.generate-api-spec: .lint-api-spec
	@echo
	@echo "================== Generate openapi.yaml file ===================="
	@echo
	echo "# NOTE: This file is auto-generated - DO NOT EDIT MANUALLY" > st2common/st2common/openapi.yaml
	echo "# Edit st2common/st2common/openapi.yaml.j2 and then run" >> st2common/st2common/openapi.yaml
	echo "# make .generate-api-spec" >> st2common/st2common/openapi.yaml
	echo "# to generate the final spec file" >> st2common/st2common/openapi.yaml
	. $(VIRTUALENV_DIR)/bin/activate; python st2common/bin/st2-generate-api-spec --config-file conf/st2.dev.conf >> st2common/st2common/openapi.yaml

.PHONY: circle-lint-api-spec
circle-lint-api-spec:
	@echo
	@echo "================== Lint API spec ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; python st2common/bin/st2-validate-api-spec --config-file conf/st2.dev.conf || echo "Open API spec lint failed."

.PHONY: flake8
flake8: requirements .flake8

.PHONY: .flake8
.flake8:
	@echo
	@echo "==================== flake ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./lint-configs/python/.flake8 $(COMPONENTS)
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./lint-configs/python/.flake8 $(COMPONENTS_RUNNERS)
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./lint-configs/python/.flake8 contrib/packs/actions/
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./lint-configs/python/.flake8 contrib/linux
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./lint-configs/python/.flake8 contrib/chatops/
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./lint-configs/python/.flake8 scripts/
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./lint-configs/python/.flake8 tools/
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./lint-configs/python/.flake8 pylint_plugins/

# Make task which verifies st2client installs and works fine
.PHONY: .st2client-install-check
.st2client-install-check:
	@echo
	@echo "==================== st2client install check ===================="
	@echo
	test -f $(VIRTUALENV_ST2CLIENT_DIR)/bin/activate || virtualenv --python=$(PYTHON_VERSION) $(VIRTUALENV_ST2CLIENT_DIR) --no-download --system-site-packages

	# Setup PYTHONPATH in bash activate script...
	# Delete existing entries (if any)
	sed -i '/_OLD_PYTHONPATHp/d' $(VIRTUALENV_ST2CLIENT_DIR)/bin/activate
	sed -i '/PYTHONPATH=/d' $(VIRTUALENV_ST2CLIENT_DIR)/bin/activate
	sed -i '/export PYTHONPATH/d' $(VIRTUALENV_ST2CLIENT_DIR)/bin/activate

	echo '_OLD_PYTHONPATH=$$PYTHONPATH' >> $(VIRTUALENV_ST2CLIENT_DIR)/bin/activate
	echo 'PYTHONPATH=${ROOT_DIR}:$(COMPONENT_PYTHONPATH)' >> $(VIRTUALENV_ST2CLIENT_DIR)/bin/activate
	echo 'export PYTHONPATH' >> $(VIRTUALENV_ST2CLIENT_DIR)/bin/activate
	touch $(VIRTUALENV_ST2CLIENT_DIR)/bin/activate
	chmod +x $(VIRTUALENV_ST2CLIENT_DIR)/bin/activate

	# NOTE We need to upgrade setuptools to avoid bug with dependency resolving in old versions
	# Setuptools 42 added support for python_requires, which is used by the configparser package,
	# which is required by the importlib-metadata package
	$(VIRTUALENV_ST2CLIENT_DIR)/bin/pip install --upgrade "pip==$(PIP_VERSION)"
	$(VIRTUALENV_ST2CLIENT_DIR)/bin/pip install --upgrade "setuptools==44.1.0"

	$(VIRTUALENV_ST2CLIENT_DIR)/bin/activate; cd st2client ; ../$(VIRTUALENV_ST2CLIENT_DIR)/bin/python setup.py install ; cd ..
	$(VIRTUALENV_ST2CLIENT_DIR)/bin/st2 --version
	$(VIRTUALENV_ST2CLIENT_DIR)/bin/python -c "import st2client"

.PHONY: bandit
bandit: requirements .bandit

.PHONY: .bandit
.bandit:
	@echo
	@echo "==================== bandit ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; bandit -r $(COMPONENTS_WITH_RUNNERS) -lll -x build,dist

.PHONY: lint
lint: requirements .lint

.PHONY: .lint
.lint: .generate-api-spec .flake8 .pylint .st2client-dependencies-check .st2common-circular-dependencies-check .rst-check .st2client-install-check

.PHONY: clean
clean: .cleanpycs

.PHONY: compile
compile:
	@echo "======================= compile ========================"
	@echo "------- Compile all .py files (syntax check test - Python 2) ------"
	@if python -c 'import compileall,re; compileall.compile_dir(".", rx=re.compile(r"/virtualenv|virtualenv-osx|virtualenv-py3|.tox|.git|.venv-st2devbox"), quiet=True)' | grep .; then exit 1; else exit 0; fi

.PHONY: compilepy3
compilepy3:
	@echo "======================= compile ========================"
	@echo "------- Compile all .py files (syntax check test - Python 3) ------"
	@if python3 -c 'import compileall,re; compileall.compile_dir(".", rx=re.compile(r"/virtualenv|virtualenv-osx|virtualenv-py3|.tox|.git|.venv-st2devbox|./st2tests/st2tests/fixtures/packs/test"), quiet=True)' | grep .; then exit 1; else exit 0; fi

.PHONY: .cleanpycs
.cleanpycs:
	@echo "Removing all .pyc files"
	find $(COMPONENTS_WITH_RUNNERS)  -name \*.pyc -type f -print0 | xargs -0 -I {} rm {}

.PHONY: .st2client-dependencies-check
.st2client-dependencies-check:
	@echo "Checking for st2common imports inside st2client"
	find ${ROOT_DIR}/st2client/st2client/ -name \*.py -type f -print0 | xargs -0 cat | grep st2common ; test $$? -eq 1

.PHONY: .st2common-circular-dependencies-check
.st2common-circular-dependencies-check:
	@echo "Checking st2common for circular dependencies"
	find ${ROOT_DIR}/st2common/st2common/ -name \*.py -type f -print0 | xargs -0 cat | grep st2reactor ; test $$? -eq 1
	find ${ROOT_DIR}/st2common/st2common/ \( -name \*.py ! -name runnersregistrar\.py -name \*.py ! -name compat\.py | -name inquiry\.py \) -type f -print0 | xargs -0 cat | grep st2actions ; test $$? -eq 1
	find ${ROOT_DIR}/st2common/st2common/ -name \*.py -type f -print0 | xargs -0 cat | grep st2api ; test $$? -eq 1
	find ${ROOT_DIR}/st2common/st2common/ -name \*.py -type f -print0 | xargs -0 cat | grep st2auth ; test $$? -eq 1
	find ${ROOT_DIR}/st2common/st2common/ -name \*.py -type f -print0 | xargs -0 cat | grep st2debug; test $$? -eq 1
	find ${ROOT_DIR}/st2common/st2common/ \( -name \*.py ! -name router\.py -name \*.py \) -type f -print0 | xargs -0 cat | grep st2stream; test $$? -eq 1
	find ${ROOT_DIR}/st2common/st2common/ -name \*.py -type f -print0 | xargs -0 cat | grep st2exporter; test $$? -eq 1

.PHONY: .cleanmongodb
.cleanmongodb:
	@echo "==================== cleanmongodb ===================="
	@echo "----- Dropping all MongoDB databases -----"
	@sudo pkill -9 mongod
	@sudo rm -rf /var/lib/mongodb/*
	@sudo chown -R mongodb:mongodb /var/lib/mongodb/
	@sudo service mongodb start
	@sleep 15
	@mongo --eval "rs.initiate()"
	@sleep 15

.PHONY: .cleanrabbitmq
.cleanrabbitmq:
	@echo "==================== cleanrabbitmq ===================="
	@echo "Deleting all RabbitMQ queue and exchanges"
	@sudo rabbitmqctl stop_app
	@sudo rabbitmqctl reset
	@sudo rabbitmqctl start_app

.PHONY: .cleancoverage
.cleancoverage:
	@echo "==================== cleancoverage ===================="
	@echo "Removing all coverage results directories"
	@echo
	rm -rf .coverage $(COVERAGE_GLOBS) \
		.coverage.unit .coverage.integration

.PHONY: distclean
distclean: clean
	@echo
	@echo "==================== distclean ===================="
	@echo
	rm -rf $(VIRTUALENV_DIR)

.PHONY: .sdist-requirements
.sdist-requirements:
	# Copy over shared dist utils module which is needed by setup.py
	@for component in $(COMPONENTS_WITH_RUNNERS); do\
		cp -f ./scripts/dist_utils.py $$component/dist_utils.py;\
		scripts/write-headers.sh $$component/dist_utils.py || break;\
	done

	# Copy over CHANGELOG.RST, CONTRIBUTING.RST and LICENSE file to each component directory
	#@for component in $(COMPONENTS_TEST); do\
	#	test -s $$component/README.rst || cp -f README.rst $$component/; \
	#	cp -f CONTRIBUTING.rst $$component/; \
	#	cp -f LICENSE $$component/; \
	#done

.PHONY: .requirements
.requirements: virtualenv
	$(VIRTUALENV_DIR)/bin/pip install --upgrade "pip==$(PIP_VERSION)"
	# Print out pip version
	$(VIRTUALENV_DIR)/bin/pip --version
	# Generate all requirements to support current CI pipeline.
	$(VIRTUALENV_DIR)/bin/python scripts/fixate-requirements.py --skip=virtualenv,virtualenv-osx -s st2*/in-requirements.txt contrib/runners/*/in-requirements.txt -f fixed-requirements.txt -o requirements.txt

	# Remove any *.egg-info files which polute PYTHONPATH
	rm -rf *.egg-info*

	# Generate finall requirements.txt file for each component
	@for component in $(COMPONENTS_WITH_RUNNERS); do\
		echo "==========================================================="; \
		echo "Generating requirements.txt for" $$component; \
		$(VIRTUALENV_DIR)/bin/python scripts/fixate-requirements.py --skip=virtualenv,virtualenv-osx -s $$component/in-requirements.txt -f fixed-requirements.txt -o $$component/requirements.txt; \
	done

	@echo "==========================================================="

.PHONY: requirements
requirements: virtualenv .requirements .sdist-requirements install-runners install-mock-runners
	@echo
	@echo "==================== requirements ===================="
	@echo
	# setuptools >= 41.0.1 is required for packs.install in dev envs
	# setuptools >= 42     is required so setup.py install respects dependencies' python_requires
	$(VIRTUALENV_DIR)/bin/pip install --upgrade "setuptools==44.1.0"
	$(VIRTUALENV_DIR)/bin/pip install --upgrade "pbr==5.4.3"  # workaround for pbr issue

	# Fix for Travis CI race
	$(VIRTUALENV_DIR)/bin/pip install "six==1.12.0"

	# Fix for Travis CI caching issue
	if [[ "$(TRAVIS_EVENT_TYPE)" != "" ]]; then\
		$(VIRTUALENV_DIR)/bin/pip uninstall -y "pytz" || echo "not installed"; \
		$(VIRTUALENV_DIR)/bin/pip uninstall -y "python-dateutil" || echo "not installed"; \
		$(VIRTUALENV_DIR)/bin/pip uninstall -y "orquesta" || echo "not installed"; \
	fi

	# Install requirements
	for req in $(REQUIREMENTS); do \
		echo "Installing $$req..." ; \
		$(VIRTUALENV_DIR)/bin/pip install $(PIP_OPTIONS) -r $$req ; \
	done

	# Install st2common package to load drivers defined in st2common setup.py
	# NOTE: We pass --no-deps to the script so we don't install all the
	# package dependencies which are already installed as part of "requirements"
	# make targets. This speeds up the build
	(cd st2common; ${ROOT_DIR}/$(VIRTUALENV_DIR)/bin/python setup.py develop --no-deps)

	# Note: We install prance here and not as part of any component
	# requirements.txt because it has a conflict with our dependency (requires
	# new version of requests) which we cant resolve at this moment
	$(VIRTUALENV_DIR)/bin/pip install "prance==0.15.0"

	# Install st2common to register metrics drivers
	# NOTE: We pass --no-deps to the script so we don't install all the
	# package dependencies which are already installed as part of "requirements"
	# make targets. This speeds up the build
	(cd ${ROOT_DIR}/st2common; ${ROOT_DIR}/$(VIRTUALENV_DIR)/bin/python setup.py develop --no-deps)

	# Install st2auth to register SSO drivers
	# NOTE: We pass --no-deps to the script so we don't install all the
	# package dependencies which are already installed as part of "requirements"
	# make targets. This speeds up the build
	(cd ${ROOT_DIR}/st2auth; ${ROOT_DIR}/$(VIRTUALENV_DIR)/bin/python setup.py develop --no-deps)

	# Some of the tests rely on submodule so we need to make sure submodules are check out
	git submodule update --recursive --remote

	# Verify there are no conflicting dependencies
	cat st2*/requirements.txt contrib/runners/*/requirements.txt | sort -u > req.txt && \
	$(VIRTUALENV_DIR)/bin/pip-compile req.txt; \
	if [[ -e req.txt ]]; then rm req.txt; fi

.PHONY: virtualenv
	# Note: We always want to update virtualenv/bin/activate file to make sure
	# PYTHONPATH is up to date and to avoid caching issues on Travis
virtualenv:
	@echo
	@echo "==================== virtualenv ===================="
	@echo
	test -f $(VIRTUALENV_DIR)/bin/activate || virtualenv --python=$(PYTHON_VERSION) $(VIRTUALENV_DIR) --no-download

	# Setup PYTHONPATH in bash activate script...
	# Delete existing entries (if any)
ifeq ($(OS),Darwin)
	echo 'Setting up virtualenv on $(OS)...'
	sed -i '' '/_OLD_PYTHONPATHp/d' $(VIRTUALENV_DIR)/bin/activate
	sed -i '' '/PYTHONPATH=/d' $(VIRTUALENV_DIR)/bin/activate
	sed -i '' '/export PYTHONPATH/d' $(VIRTUALENV_DIR)/bin/activate
else
	echo 'Setting up virtualenv on $(OS)...'
	sed -i '/_OLD_PYTHONPATHp/d' $(VIRTUALENV_DIR)/bin/activate
	sed -i '/PYTHONPATH=/d' $(VIRTUALENV_DIR)/bin/activate
	sed -i '/export PYTHONPATH/d' $(VIRTUALENV_DIR)/bin/activate
endif

	echo '_OLD_PYTHONPATH=$$PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate
	#echo 'PYTHONPATH=$$_OLD_PYTHONPATH:$(COMPONENT_PYTHONPATH)' >> $(VIRTUALENV_DIR)/bin/activate
	echo 'PYTHONPATH=${ROOT_DIR}:$(COMPONENT_PYTHONPATH)' >> $(VIRTUALENV_DIR)/bin/activate
	echo 'export PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate
	touch $(VIRTUALENV_DIR)/bin/activate

	# Setup PYTHONPATH in fish activate script...
	#echo '' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo 'set -gx _OLD_PYTHONPATH $$PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo 'set -gx PYTHONPATH $$_OLD_PYTHONPATH $(COMPONENT_PYTHONPATH)' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo 'functions -c deactivate old_deactivate' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo 'function deactivate' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo '  if test -n $$_OLD_PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo '    set -gx PYTHONPATH $$_OLD_PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo '    set -e _OLD_PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo '  end' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo '  old_deactivate' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo '  functions -e old_deactivate' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo 'end' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#touch $(VIRTUALENV_DIR)/bin/activate.fish

.PHONY: tests
tests: pytests

.PHONY: pytests
pytests: compilepy3 requirements .flake8 .pylint .pytests-coverage

.PHONY: .pytests
.pytests: compile .configgen .generate-api-spec .unit-tests clean

.PHONY: .pytests-coverage
.pytests-coverage: .unit-tests-coverage-html clean

.PHONY: unit-tests
unit-tests: requirements .unit-tests

.PHONY: .unit-tests
.unit-tests:
	@echo
	@echo "==================== tests ===================="
	@echo
	@echo "----- Dropping st2-test db -----"
	@mongo st2-test --eval "db.dropDatabase();"
	@for component in $(COMPONENTS_TEST); do\
		echo "==========================================================="; \
		echo "Running tests in" $$component; \
		echo "-----------------------------------------------------------"; \
		. $(VIRTUALENV_DIR)/bin/activate; \
		    nosetests $(NOSE_OPTS) -s -v \
		    $$component/tests/unit || exit 1; \
		echo "-----------------------------------------------------------"; \
		echo "Done running tests in" $$component; \
		echo "==========================================================="; \
	done

.PHONY: .run-unit-tests-coverage
ifdef INCLUDE_TESTS_IN_COVERAGE
.run-unit-tests-coverage: NOSE_COVERAGE_PACKAGES := $(NOSE_COVERAGE_PACKAGES),tests.unit
endif
.run-unit-tests-coverage:
	@echo
	@echo "==================== unit tests with coverage  ===================="
	@echo
	@echo "----- Dropping st2-test db -----"
	@mongo st2-test --eval "db.dropDatabase();"
	for component in $(COMPONENTS_TEST); do\
		echo "==========================================================="; \
		echo "Running tests in" $$component; \
		echo "-----------------------------------------------------------"; \
		. $(VIRTUALENV_DIR)/bin/activate; \
		    COVERAGE_FILE=.coverage.unit.$$(echo $$component | tr '/' '.') \
		    nosetests $(NOSE_OPTS) -s -v $(NOSE_COVERAGE_FLAGS) \
		    $(NOSE_COVERAGE_PACKAGES) \
		    $$component/tests/unit || exit 1; \
		echo "-----------------------------------------------------------"; \
		echo "Done running tests in" $$component; \
		echo "==========================================================="; \
	done

.PHONY: .combine-unit-tests-coverage
.combine-unit-tests-coverage: .run-unit-tests-coverage
	@if [ -n "$(NOSE_COVERAGE_FLAGS)" ]; then \
	    . $(VIRTUALENV_DIR)/bin/activate; COVERAGE_FILE=.coverage.unit \
	        coverage combine .coverage.unit.*; \
	fi

.coverage.unit:
	@if compgen -G '.coverage.unit.*'; then \
		for coverage_result in $$(compgen -G '.coverage.unit.*'); do \
			echo "Combining data from $${coverage_result}"; \
			. $(VIRTUALENV_DIR)/bin/activate; COVERAGE_FILE=.coverage.unit \
			coverage combine $${coverage_result}; \
		done; \
	else \
		echo "Running unit tests"; \
		make .combine-unit-tests-coverage; \
	fi

.PHONY: .report-unit-tests-coverage
.report-unit-tests-coverage: .coverage.unit
	@if [ -n "$(NOSE_COVERAGE_FLAGS)" ]; then \
	    . $(VIRTUALENV_DIR)/bin/activate; COVERAGE_FILE=.coverage.unit \
	        coverage report; \
	fi

.PHONY: .unit-tests-coverage-html
.unit-tests-coverage-html: .coverage.unit
	@if [ -n "$(NOSE_COVERAGE_FLAGS)" ]; then \
	    . $(VIRTUALENV_DIR)/bin/activate; COVERAGE_FILE=.coverage.unit \
	        coverage html; \
	fi

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
		echo "-----------------------------------------------------------"; \
		. $(VIRTUALENV_DIR)/bin/activate; \
		    nosetests $(NOSE_OPTS) -s -v \
		    $$component/tests/integration || exit 1; \
		echo "-----------------------------------------------------------"; \
		echo "Done running tests in" $$component; \
		echo "==========================================================="; \
	done

.PHONY: .run-integration-tests-coverage
ifdef INCLUDE_TESTS_IN_COVERAGE
.run-integration-tests-coverage: NOSE_COVERAGE_PACKAGES := $(NOSE_COVERAGE_PACKAGES),tests.integration
endif
.run-integration-tests-coverage:
	@echo
	@echo "================ integration tests with coverage ================"
	@echo
	@echo "----- Dropping st2-test db -----"
	@mongo st2-test --eval "db.dropDatabase();"
	@for component in $(COMPONENTS_TEST); do\
		echo "==========================================================="; \
		echo "Running tests in" $$component; \
		echo "-----------------------------------------------------------"; \
		. $(VIRTUALENV_DIR)/bin/activate; \
		    COVERAGE_FILE=.coverage.integration.$$(echo $$component | tr '/' '.') \
		    nosetests $(NOSE_OPTS) -s -v $(NOSE_COVERAGE_FLAGS) \
		    $(NOSE_COVERAGE_PACKAGES) \
		    $$component/tests/integration || exit 1; \
		echo "-----------------------------------------------------------"; \
		echo "Done running tests in" $$component; \
		echo "==========================================================="; \
	done
	@echo
	@echo "============== runners integration tests with coverage =============="
	@echo
	@echo "The tests assume st2 is running on 127.0.0.1."
	@for component in $(COMPONENTS_RUNNERS); do\
		echo "==========================================================="; \
		echo "Running tests in" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate; \
		    COVERAGE_FILE=.coverage.integration.$$(echo $$component | tr '/' '.') \
			nosetests $(NOSE_OPTS) -s -v \
			$(NOSE_COVERAGE_FLAGS) $(NOSE_COVERAGE_PACKAGES) $$component/tests/integration || exit 1; \
	done
	@echo
	@echo "==================== Orquesta integration tests with coverage (HTML reports) ===================="
	@echo "The tests assume st2 is running on 127.0.0.1."
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; \
		COVERAGE_FILE=.coverage.integration.orquesta \
		nosetests $(NOSE_OPTS) -s -v \
		$(NOSE_COVERAGE_FLAGS) $(NOSE_COVERAGE_PACKAGES) st2tests/integration/orquesta || exit 1; \


.PHONY: .combine-integration-tests-coverage
.combine-integration-tests-coverage: .run-integration-tests-coverage
	@if [ -n "$(NOSE_COVERAGE_FLAGS)" ]; then \
	    . $(VIRTUALENV_DIR)/bin/activate; COVERAGE_FILE=.coverage.integration \
	        coverage combine .coverage.integration.*; \
	fi

.coverage.integration:
	@if compgen -G '.coverage.integration.*'; then \
		for coverage_result in $$(compgen -G '.coverage.integration.*'); do \
			echo "Combining data from $${coverage_result}"; \
			. $(VIRTUALENV_DIR)/bin/activate; COVERAGE_FILE=.coverage.integration \
			coverage combine $${coverage_result}; \
		done; \
	else \
		echo "Running integration tests"; \
		make .combine-integration-tests-coverage; \
	fi

.PHONY: .report-integration-tests-coverage
.report-integration-tests-coverage: .coverage.integration
	@if [ -n "$(NOSE_COVERAGE_FLAGS)" ]; then \
	    . $(VIRTUALENV_DIR)/bin/activate; COVERAGE_FILE=.coverage.integration \
	        coverage report; \
	fi

.PHONY: .integration-tests-coverage-html
.integration-tests-coverage-html: .coverage.integration
	@if [ -n "$(NOSE_COVERAGE_FLAGS)" ]; then \
	    . $(VIRTUALENV_DIR)/bin/activate; COVERAGE_FILE=.coverage.integration \
	        coverage html; \
	fi

.PHONY: .itests-coverage-html
.itests-coverage-html: .integration-tests-coverage-html

.PHONY: .coverage-combine
.coverage-combine: .run-unit-tests-coverage .run-integration-tests-coverage
	. $(VIRTUALENV_DIR)/bin/activate; coverage combine $(COVERAGE_GLOBS)

# This is a real target, but we need to do our own make trickery in case some
# but not all of the prerequisites are available
.coverage:
	@NUM_COVERAGE_RESULTS=0; \
	for coverage_result in $$( \
		for coverage_glob in $(COVERAGE_GLOBS_QUOTED); do \
			compgen -G $${coverage_glob}; \
		done; \
	); do \
		NUM_COVERAGE_RESULTS=$$(( NUM_COVERAGE_RESULTS+1 )); \
		echo "Combining $${coverage_result}: $$NUM_COVERAGE_RESULTS"; \
		. $(VIRTUALENV_DIR)/bin/activate; coverage combine $${coverage_result}; \
	done; \
	if [ $${NUM_COVERAGE_RESULTS} -eq 0 ]; then \
		make .coverage-combine; \
	fi

# @for coverage_result in $(COVERAGE_GLOBS); do \
# 	[ -e $${coverage_result} ] || echo "$${coverage_result} does not exist." && continue; \
# 	echo "Combining data from $${coverage_result}"; \
# 	. $(VIRTUALENV_DIR)/bin/activate; coverage combine $${coverage_result}; \
# done || \
# (echo "Running .coverage-combine"; make .coverage-combine)

.PHONY: .coverage-report
.coverage-report: .coverage
	. $(VIRTUALENV_DIR)/bin/activate; coverage report

.PHONY: .coverage-html
.coverage-html: .coverage
	. $(VIRTUALENV_DIR)/bin/activate; coverage html

.PHONY: orquesta-itests
orquesta-itests: requirements .orquesta-itests

.PHONY: .orquesta-itests
.orquesta-itests:
	@echo
	@echo "==================== Orquesta integration tests ===================="
	@echo "The tests assume st2 is running on 127.0.0.1."
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; nosetests $(NOSE_OPTS) -s -v st2tests/integration/orquesta || exit 1;

.PHONY: .orquesta-itests-coverage-html
.orquesta-itests-coverage-html:
	@echo
	@echo "==================== Orquesta integration tests with coverage (HTML reports) ===================="
	@echo "The tests assume st2 is running on 127.0.0.1."
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; nosetests $(NOSE_OPTS) -s -v --with-coverage \
        --cover-inclusive --cover-html st2tests/integration/orquesta || exit 1;

.PHONY: packs-tests
packs-tests: requirements .packs-tests

.PHONY: .packs-tests
.packs-tests:
	@echo
	@echo "==================== packs-tests ===================="
	@echo
	# Install st2common to register metrics drivers
	(cd ${ROOT_DIR}/st2common; ${ROOT_DIR}/$(VIRTUALENV_DIR)/bin/python setup.py develop --no-deps)
	. $(VIRTUALENV_DIR)/bin/activate; find ${ROOT_DIR}/contrib/* -maxdepth 0 -type d -print0 | xargs -0 -I FILENAME ./st2common/bin/st2-run-pack-tests -c -t -x -p FILENAME


.PHONY: runners-tests
runners-tests: requirements .runners-tests

.PHONY: .runners-tests
.runners-tests:
	@echo
	@echo "==================== runners-tests ===================="
	@echo
	@echo "----- Dropping st2-test db -----"
	@mongo st2-test --eval "db.dropDatabase();"
	@for component in $(COMPONENTS_RUNNERS); do\
		echo "==========================================================="; \
		echo "Running tests in" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate; nosetests $(NOSE_OPTS) -s -v $$component/tests/unit || exit 1; \
	done

.PHONY: runners-itests
runners-itests: requirements .runners-itests

.PHONY: .runners-itests
.runners-itests:
	@echo
	@echo "==================== runners-itests ===================="
	@echo
	@echo "----- Dropping st2-test db -----"
	@for component in $(COMPONENTS_RUNNERS); do\
		echo "==========================================================="; \
		echo "Running tests in" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate; nosetests $(NOSE_OPTS) -s -v $$component/tests/integration || exit 1; \
	done

.PHONY: .runners-itests-coverage-html
.runners-itests-coverage-html:
	@echo
	@echo "============== runners-itests-coverage-html =============="
	@echo
	@echo "The tests assume st2 is running on 127.0.0.1."
	@for component in $(COMPONENTS_RUNNERS); do\
		echo "==========================================================="; \
		echo "Running tests in" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate; nosetests $(NOSE_OPTS) -s -v --with-coverage \
			--cover-inclusive --cover-html $$component/tests/integration || exit 1; \
	done

.PHONY: cli
cli:
	@echo
	@echo "=================== Building st2 client ==================="
	@echo
	pushd $(CURDIR) && cd st2client && ((python setup.py develop || printf "\n\n!!! ERROR: BUILD FAILED !!!\n") || popd)

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


.PHONY: ci
ci: ci-checks ci-unit ci-integration ci-packs-tests

.PHONY: ci-checks
ci-checks: compilepy3 .generated-files-check .pylint .flake8 check-requirements check-sdist-requirements .st2client-dependencies-check .st2common-circular-dependencies-check circle-lint-api-spec .rst-check .st2client-install-check check-python-packages

.PHONY: ci-py3-unit
ci-py3-unit:
	@echo
	@echo "==================== ci-py3-unit ===================="
	@echo
	NOSE_WITH_TIMER=$(NOSE_WITH_TIMER) tox -e py36-unit -vv

.PHONY: ci-py3-packs-tests
ci-py3-packs-tests:
	@echo
	@echo "==================== ci-py3-packs-tests ===================="
	@echo
	NOSE_WITH_TIMER=$(NOSE_WITH_TIMER) tox -e py36-packs -vv

.PHONY: ci-py3-integration
ci-py3-integration: requirements .ci-prepare-integration .ci-py3-integration

.PHONY: .ci-py3-integration
.ci-py3-integration:
	@echo
	@echo "==================== ci-py3-integration ===================="
	@echo
	NOSE_WITH_TIMER=$(NOSE_WITH_TIMER) tox -e py36-integration -vv

.PHONY: .rst-check
.rst-check:
	@echo
	@echo "==================== rst-check ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; rstcheck --report warning CHANGELOG.rst

.PHONY: .generated-files-check
.generated-files-check:
	# Verify that all the files which are automatically generated have indeed been re-generated and
	# committed
	@echo "==================== generated-files-check ===================="

	# 1. Sample config - conf/st2.conf.sample
	cp conf/st2.conf.sample /tmp/st2.conf.sample.upstream
	make .configgen
	diff conf/st2.conf.sample /tmp/st2.conf.sample.upstream || (echo "conf/st2.conf.sample hasn't been re-generated and committed. Please run \"make configgen\" and include and commit the generated file." && exit 1)
	# 2. OpenAPI definition file - st2common/st2common/openapi.yaml (generated from
	# st2common/st2common/openapi.yaml.j2)
	cp st2common/st2common/openapi.yaml /tmp/openapi.yaml.upstream
	make .generate-api-spec
	diff st2common/st2common/openapi.yaml  /tmp/openapi.yaml.upstream || (echo "st2common/st2common/openapi.yaml hasn't been re-generated and committed. Please run \"make generate-api-spec\" and include and commit the generated file." && exit 1)
	# 3. Schemas for the content models - st2common/bin/st2-generate-schemas
	cp contrib/schemas/pack.json /tmp/pack.json.upstream
	cp contrib/schemas/action.json /tmp/action.json.upstream
	cp contrib/schemas/alias.json /tmp/alias.json.upstream
	cp contrib/schemas/policy.json /tmp/policy.json.upstream
	cp contrib/schemas/rule.json /tmp/rule.json.upstream
	make .schemasgen
	diff contrib/schemas/pack.json /tmp/pack.json.upstream || (echo "contrib/schemas/pack.json hasn't been re-generated and committed. Please run \"make schemasgen\" and include and commit the generated file." && exit 1)
	diff contrib/schemas/action.json /tmp/action.json.upstream || (echo "contrib/schemas/pack.json hasn't been re-generated and committed. Please run \"make schemasgen\" and include and commit the generated file." && exit 1)
	diff contrib/schemas/alias.json /tmp/alias.json.upstream || (echo "contrib/schemas/pack.json hasn't been re-generated and committed. Please run \"make schemasgen\" and include and commit the generated file." && exit 1)
	diff contrib/schemas/policy.json /tmp/policy.json.upstream || (echo "contrib/schemas/pack.json hasn't been re-generated and committed. Please run \"make schemasgen\" and include and commit the generated file." && exit 1)
	diff contrib/schemas/rule.json /tmp/rule.json.upstream || (echo "contrib/schemas/pack.json hasn't been re-generated and committed. Please run \"make schemasgen\" and include and commit the generated file." && exit 1)
	@echo "All automatically generated files are up to date."

.PHONY: ci-unit
ci-unit: .unit-tests-coverage-html

.PHONY: .ci-prepare-integration
.ci-prepare-integration:
	sudo -E ./scripts/travis/prepare-integration.sh

.PHONY: ci-integration
ci-integration: .ci-prepare-integration .itests-coverage-html

.PHONY: ci-runners
ci-runners: .ci-prepare-integration .runners-itests-coverage-html

.PHONY: ci-orquesta
ci-orquesta: .ci-prepare-integration .orquesta-itests-coverage-html

.PHONY: ci-packs-tests
ci-packs-tests: .packs-tests
