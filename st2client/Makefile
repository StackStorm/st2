SHELL := /bin/bash
RPM_ROOT=~/rpmbuild
RPM_SOURCES_DIR := $(RPM_ROOT)/SOURCES/
RPM_SPECS_DIR := $(RPM_ROOT)/SPECS/
VER=0.4.0
RELEASE=1
COMPONENTS := st2client

.PHONY: rpm
rpm: 
	python setup.py bdist_rpm
	mkdir -p $(RPM_ROOT)/RPMS/noarch
	cp dist/$(COMPONENTS)-$(VER)*noarch.rpm $(RPM_ROOT)/RPMS/noarch/$(COMPONENTS)-$(VER)-$(RELEASE).noarch.rpm
	cp dist/*src.rpm $(RPM_ROOT)/SRPMS/$(COMPONENTS)-$(VER)-$(RELEASE).src.rpm
	rm -Rf dist pbr-0.8.2-py2.7.egg st2client.egg-info ChangeLog AUTHORS build

.PHONY: deb
deb:
	mkdir -p ~/debbuild
	rm -Rf ~/.local
	python setup.py install --user
	cp -R ~/.local/bin ./
	tar --transform=s~^~$(COMPONENTS)-$(VER)/~ -czf ~/$(COMPONENTS).tar.gz bin $(COMPONENTS) packaging/debian
	pushd ~ && tar -xzf $(COMPONENTS).tar.gz && cd $(COMPONENTS)-$(VER) && cp -Rf packaging/debian ./ && dpkg-buildpackage -us -uc -b && popd
	cp -f ~/$(COMPONENT)*.deb ~/debbuild
