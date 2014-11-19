SHELL := /bin/bash
RPM_ROOT=~/rpmbuild
RPM_SOURCES_DIR := $(RPM_ROOT)/SOURCES/
RPM_SPECS_DIR := $(RPM_ROOT)/SPECS/
VER := $(shell cat ./st2client/__init__.py | grep -Po "__version__ = '\K[^']*")
RELEASE=1
COMPONENTS := st2client

.PHONY: rpm
rpm: 
	python setup.py bdist_rpm
	mkdir -p $(RPM_ROOT)/RPMS/noarch
	cp dist/$(COMPONENTS)-$(VER)*noarch.rpm $(RPM_ROOT)/RPMS/noarch/$(COMPONENTS)-$(VER)-$(RELEASE).noarch.rpm
	mkdir -p $(RPM_ROOT)/SRPMS
	cp dist/*src.rpm $(RPM_ROOT)/SRPMS/$(COMPONENTS)-$(VER)-$(RELEASE).src.rpm
	rm -Rf dist pbr-0.8.2-py2.7.egg $(COMPONENTS).egg-info ChangeLog AUTHORS build

.PHONY: deb
deb:
	python setup.py --command-packages=stdeb.command bdist_deb
	mkdir -p ~/debbuild
	cp deb_dist/python-$(COMPONENTS)_$(VER)-$(RELEASE)_all.deb ~/debbuild/$(COMPONENTS)_$(VER)-$(RELEASE)_all.deb
	rm -Rf dist deb_dist $(COMPONENTS)-$(VER).tar.gz $(COMPONENTS).egg-info ChangeLog AUTHORS build
