Summary: ST2 Common Libraries
Name: st2common
Version: 0.4.0
Release: 1
License: Apache
Group: Applications/Engineering
BuildArch: noarch
Source: /opt/git/st2/st2common.tar.gz
URL: https://github.com/StackStorm/st2
Vendor: StackStorm
Packager: Estee Tew <st2@stackstorm.com>
Requires:	python-devel
Requires:   	python-pip

%description
An automation plaform that needs a much better description than this.

%prep
%setup

%build
# Empty section.

%install

mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/local/lib/python2.7/site-packages/
mkdir -p %{buildroot}/var/log/st2
mkdir -p %{buildroot}/etc/st2
mkdir -p %{buildroot}/opt/stackstorm/packs
mkdir -p %{buildroot}/opt/stackstorm/packs/default
mkdir -p %{buildroot}/opt/stackstorm/packs/default/actions
mkdir -p %{buildroot}/opt/stackstorm/packs/default/sensors
mkdir -p %{buildroot}/opt/stackstorm/packs/default/rules
mkdir -p %{buildroot}/usr/share/doc/st2
mkdir -p %{buildroot}/usr/share/stackstorm
cp -R contrib/core %{buildroot}/opt/stackstorm/packs/
cp -R contrib/packs %{buildroot}/opt/stackstorm/packs/
cp -R contrib/linux %{buildroot}/opt/stackstorm/packs/
cp -R contrib/examples %{buildroot}/usr/share/doc/st2/
cp -R contrib/tests %{buildroot}/usr/share/stackstorm/
cp -R docs/* %{buildroot}/usr/share/doc/st2/
cp -R st2common %{buildroot}//usr/local/lib/python2.7/site-packages/
cp -R bin %{buildroot}/usr/local/lib/python2.7/site-packages/st2common/
install st2/st2.conf %{buildroot}/etc/st2/st2.conf
install logrotate.d/st2.conf %{buildroot}/etc/logrotate.d/st2.conf
install -m755 tools/st2ctl %{buildroot}/usr/bin/st2ctl
install -m755 tools/st2-setup-tests %{buildroot}/usr/local/lib/python2.7/site-packages/st2common/bin/st2-setup-tests
install -m755 tools/st2-setup-examples %{buildroot}/usr/local/lib/python2.7/site-packages/st2common/bin/st2-setup-examples
install -m755 tools/st2-self-check %{buildroot}/usr/local/lib/python2.7/site-packages/st2common/bin/st2-self-check

%files
/usr/local/lib/python2.7/site-packages/st2common*
/usr/share/doc/st2/*
/usr/share/stackstorm/*
/etc/st2/*
/opt/stackstorm/*
/var/log/st2
/usr/bin/st2ctl
