SHELL := /bin/bash
RPM_ROOT=~/rpmbuild
RPM_SOURCES_DIR := $(RPM_ROOT)/SOURCES/
RPM_SPECS_DIR := $(RPM_ROOT)/SPECS/
VER=0.4.0

COMPONENTS := st2common

.PHONY: rpm
rpm: 
	pushd ~ && rpmdev-setuptree && popd
	mkdir -p stanley && cp -Rf ../conf/* stanley/
	tar --transform=s~^~$(COMPONENTS)-$(VER)/~ --exclude=correlation -czf $(RPM_SOURCES_DIR)/$(COMPONENTS).tar.gz bin stanley $(COMPONENTS) ../contrib ../docs ../requirements.txt
	cp packaging/rpm/$(COMPONENTS).spec $(RPM_SPECS_DIR)/
	cd $(RPM_SPECS_DIR) && rpmbuild --clean --rmsource -ba $(COMPONENTS).spec

.PHONY: deb
deb:
	mkdir -p ~/debbuild
	mkdir -p stanley && cp -Rf ../conf/* stanley/
	tar --transform=s~^~$(COMPONENTS)-$(VER)/~ --exclude=correlation -czf ~/$(COMPONENTS).tar.gz bin stanley $(COMPONENTS) ../contrib ../docs ../requirements.txt packaging/debian
	pushd ~ && tar -xzf $(COMPONENTS).tar.gz && cd $(COMPONENTS)-$(VER) && cp -Rf packaging/debian ./ && dpkg-buildpackage -us -uc -b && popd
	cp -f ~/$(COMPONENT)*.deb ~/debbuild/

