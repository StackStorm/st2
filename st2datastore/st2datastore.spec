Summary: Stanley Datastore
Name: st2datastore
Version: 0.1.0
Release: 1
License: license
Group: Applications/Engineering
BuildArch: noarch
Source: /opt/git/stanley/st2datastore.tar.gz
URL: https://github.com/StackStorm/stanley
Vendor: StackStorm
Packager: Stormin Stanley <stanley@stackstorm.com>
Requires:     st2common

%description
An automation plaform that needs a much better description than this.

%prep
%setup

%build
sed -i -r "s~logs~/var/log/stanley~g" conf/logging.conf

%install

mkdir -p %{buildroot}%{python2_sitelib}
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/etc/st2datastore
cp -R st2datastore %{buildroot}%{python2_sitelib}/
cp -R conf/* %{buildroot}/etc/st2datastore/
install -m755 bin/datastore_controller %{buildroot}/usr/bin/datastore_controller

%files

/usr/lib/python2.7/site-packages/st2datastore*
/usr/bin/datastore_controller
/etc/st2datastore*
