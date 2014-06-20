REPO_ROOT := ..
VIRTUALENV_DIR=virtualenv
RPM_ROOT=~/rpmbuild
RPM_SOURCES_DIR := $(RPM_ROOT)/SOURCES/
RPM_SPECS_DIR := $(RPM_ROOT)/SPECS/
COMPONENTS := st2actioncontroller
VER=0.1.0
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

.PHONY: rpm
rpm: 
	pushd ~ && rpmdev-setuptree && popd
	tar --transform=s~^~$(COMPONENTS)-$(VER)/~ -czf $(RPM_SOURCES_DIR)/$(COMPONENTS)-$(VER).tar.gz bin conf public $(COMPONENTS)
	cp $(COMPONENTS)-$(VER).spec $(RPM_SPECS_DIR)/
	cd $(RPM_SPECS_DIR)
	rpmbuild --clean --rmsource -ba $(COMPONENTS)-$(VER).spec
