TOX_DIR := .tox
#VIRTUALENV_DIR := $(TOX_DIR)/py27
VIRTUALENV_DIR := virtualenv

BINARIES := bin

# All components are prefixed by st2
#COMPONENTS := st2common st2actioncontroller st2reactor
COMPONENTS := $(wildcard st2*)
COMPONENTS_TEST := $(wildcard st2*/tests)

EXTERNAL_DIR := external

# nasty hack to get a space into a variable
space_char :=
space_char +=
COMPONENT_PYTHONPATH = $(subst $(space_char),:,$(realpath $(COMPONENTS)))

PYTHON_TARGET := 2.7
REQUIREMENTS := requirements.txt test-requirements.txt

.PHONY: all
all: requirements tests

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
tests:
	. $(VIRTUALENV_DIR)/bin/activate; nosetests -v $(COMPONENTS_TEST)
