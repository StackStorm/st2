SHELL := /bin/bash
RPM_ROOT=~/rpmbuild
RPM_SOURCES_DIR := $(RPM_ROOT)/SOURCES/
RPM_SPECS_DIR := $(RPM_ROOT)/SPECS/
VER=0.4.0

COMPONENTS := st2common

.PHONY: rpm
rpm:
	pushd ~ && rpmdev-setuptree && popd
	mkdir -p st2 && cp -f ../conf/st2.prod.conf st2/st2.conf
	mkdir -p logrotate.d && cp -f ../conf/logrotate.conf logrotate.d/st2.conf
	tar --transform=s~^~$(COMPONENTS)-$(VER)/~ --exclude=correlation -czf $(RPM_SOURCES_DIR)/$(COMPONENTS).tar.gz bin st2 logrotate.d $(COMPONENTS) ../contrib ../docs ../tools/ ../requirements.txt
	cp packaging/rpm/$(COMPONENTS).spec $(RPM_SPECS_DIR)/
	cd $(RPM_SPECS_DIR) && rpmbuild --clean --rmsource -ba $(COMPONENTS).spec

.PHONY: rhel-rpm
rhel-rpm:
	pushd ~ && rpmdev-setuptree && popd
	mkdir -p st2 && cp -f ../conf/st2.prod.conf st2/st2.conf
	mkdir -p logrotate.d && cp -f ../conf/logrotate.conf logrotate.d/st2.conf
	sed -i '/\[actionrunner\]/a python_binary = /usr/bin/python2.7' st2/st2.conf
	tar --transform=s~^~$(COMPONENTS)-$(VER)/~ --exclude=correlation -czf $(RPM_SOURCES_DIR)/$(COMPONENTS).tar.gz bin st2 logrotate.d $(COMPONENTS) ../contrib ../docs ../tools/ ../requirements.txt
	cp packaging/rpm/$(COMPONENTS)-rhel6.spec $(RPM_SPECS_DIR)/
	cd $(RPM_SPECS_DIR) && rpmbuild --clean --rmsource -ba $(COMPONENTS)-rhel6.spec

.PHONY: deb
deb:
	mkdir -p ~/debbuild
	mkdir -p st2 && cp -f ../conf/st2.prod.conf st2/st2.conf
	mkdir -p logrotate.d && cp -f ../conf/logrotate.conf logrotate.d/st2.conf
	tar --transform=s~^~$(COMPONENTS)-$(VER)/~ --exclude=correlation -czf ~/$(COMPONENTS).tar.gz bin st2 logrotate.d $(COMPONENTS) ../contrib ../docs ../tools/ ../requirements.txt packaging/debian
	pushd ~ && tar -xzf $(COMPONENTS).tar.gz && cd $(COMPONENTS)-$(VER) && cp -Rf packaging/debian ./ && dpkg-buildpackage -us -uc -b && popd
	cp -f ~/$(COMPONENT)*.deb ~/debbuild/
