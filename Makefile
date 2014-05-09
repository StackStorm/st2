TOX_DIR := .tox
#VIRTUALENV_DIR := $(TOX_DIR)/py27
VIRTUALENV_DIR := virtualenv

BINARIES := bin

# All components are prefixed by st2
COMPONENTS := $(wildcard st2*)

# Components that implement a component-controlled test-runner. These components provide an
# in-component Makefile. (Temporary fix until I can generalize the pecan unittest setup. -mar)
COMPONENT_SPECIFIC_TESTS := st2stactioncontroller

EXTERNAL_DIR := external

# nasty hack to get a space into a variable
space_char :=
space_char +=
COMPONENT_PYTHONPATH = $(subst $(space_char),:,$(realpath $(COMPONENTS)))
COMPONENTS_TEST := $(foreach component,$(filter-out $(COMPONENT_SPECIFIC_TESTS),$(COMPONENTS)),$(component)/tests)

PYTHON_TARGET := 2.7
REQUIREMENTS := requirements.txt test-requirements.txt

.PHONY: all
all: requirements tests

# Target for debugging Makefile variable assembly
.PHONY: play
play:
	echo $(COMPONENTS_TEST)

.PHONY: distclean
distclean:
	@echo $(COMPONENTS)
	rm -rf $(VIRTUALENV_DIR)

.PHONY: requirements
requirements: virtualenv requirements.txt test-requirements.txt
	. $(VIRTUALENV_DIR)/bin/activate ; pip install -U $(foreach req,$(REQUIREMENTS),-r $(req))

.PHONY: virtualenv
virtualenv: $(VIRTUALENV_DIR)/bin/activate
$(VIRTUALENV_DIR)/bin/activate:
	@echo ""
	@echo "Creating python virtual environment"
	@echo
	test -d $(VIRTUALENV_DIR) || virtualenv --no-site-packages $(VIRTUALENV_DIR)

	# Setup PYTHONPATH in bash activate script...
	echo '' >> $(VIRTUALENV_DIR)/bin/activate
	echo '_OLD_PYTHONPATH=$$PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate
	echo 'PYTHONPATH=$$_OLD_PYTHONPATH:$(COMPONENT_PYTHONPATH):$(EXTERNAL_DIR)' >> $(VIRTUALENV_DIR)/bin/activate
	echo 'export PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate
	touch $(VIRTUALENV_DIR)/bin/activate

.PHONY: tests
tests: requirements
	. $(VIRTUALENV_DIR)/bin/activate; nosetests -v $(COMPONENTS_TEST)
