Summary: Stanley Datastore Controller
Name: st2datastore
Version: 0.1.0
Release: 1
License: license
Group: Applications/Engineering
Source: /opt/git/stanley/st2datastore-0.1.0.tar.gz
URL: https://github.com/StackStorm/stanley
Vendor: StackStorm
Packager: Stormin Stanley <stanley@stackstorm.com>
Requires: st2common

%description
An automation plaform that needs a much better description than this.

%prep
%setup

%build

%install

mkdir -p %{buildroot}/etc/st2datastore
mkdir -p %{buildroot}%{python2_sitelib}
mkdir -p %{buildroot}/usr/bin/
cp -R st2datastore %{buildroot}/%{python2_sitelib}/
cp -R conf/* %{buildroot}/etc/st2datastore
install -m755 bin/datastore_controller %{buildroot}/usr/bin/datastore_controller

%files

/usr/lib/python2.7/site-packages/st2datastore*
/usr/bin/st2datastore
/etc/st2datastore*
