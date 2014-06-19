REPO_ROOT := ..
VIRTUALENV_DIR=virtualenv
RPM_ROOT=~/rpmbuild
RPM_SOURCES_DIR := $(RPM_ROOT)/SOURCES/
RPM_SPECS_DIR := $(RPM_ROOT)/SPECS/
VER=0.1.0

COMPONENTS := st2reactorcontroller

.PHONY: clean
clean:
	rm -rf *.egg-info
	find . -name \*.pyc -type f -delete
	find . -name \*.pyo -type f -delete

.PHONY: test
test:
	. ../$(VIRTUALENV_DIR)/bin/activate; PECAN_CONFIG=tests/config.py python setup.py test -q

.PHONY: rpm
rpm: 
	pushd ~ && rpmdev-setuptree && popd
	tar --transform=s~^~$(COMPONENTS)-$(VER)/~ -czf $(RPM_SOURCES_DIR)/$(COMPONENTS)-$(VER).tar.gz bin conf public $(COMPONENTS)
	cp $(COMPONENTS)-$(VER).spec $(RPM_SPECS_DIR)/
	cd $(RPM_SPECS_DIR)
	rpmbuild --clean --rmsource -ba $(COMPONENTS)-$(VER).spec

