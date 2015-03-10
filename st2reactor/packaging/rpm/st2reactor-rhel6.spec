Summary: ST2 reactor
Name: st2reactor
Version: 0.4.0
Release: 1
License: Apache
Group: Applications/Engineering
BuildArch: noarch
Source: /opt/git/st2/st2reactor.tar.gz
URL: https://github.com/StackStorm/st2
Vendor: StackStorm
Packager: Estee Tew <st2@stackstorm.com>
Requires:     st2common

%description
An automation plaform that needs a much better description than this.

%prep
%setup

%build
sed -i -r "s~logs~/var/log/st2~g" conf/logging*.conf

%install

mkdir -p %{buildroot}/usr/local/lib/python2.7/site-packages/
mkdir -p %{buildroot}/etc/st2reactor
mkdir -p %{buildroot}/usr/bin/
cp -R st2reactor %{buildroot}/usr/local/lib/python2.7/site-packages/
cp -R conf/* %{buildroot}/etc/st2reactor
install -m755 bin/sensor_container %{buildroot}/usr/bin/sensor_container
install -m755 bin/rules_engine %{buildroot}/usr/bin/rules_engine
install -m755 bin/rule_tester %{buildroot}/usr/bin/rule_tester

%files

/usr/local/lib/python2.7/site-packages/st2reactor*
/usr/bin/sensor_container
/usr/bin/rules_engine
/usr/bin/rule_tester
/etc/st2reactor*
