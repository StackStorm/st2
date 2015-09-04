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

%include %{_rpmconfigdir}/macros.python

%description
An automation plaform that needs a much better description than this.

%prep
%setup

%build
sed -i -r "s~logs~/var/log/st2~g" conf/logging*.conf

%install

mkdir -p %{buildroot}%{python2_sitelib}
mkdir -p %{buildroot}/etc/st2reactor
mkdir -p %{buildroot}/usr/bin/
cp -R st2reactor %{buildroot}%{python2_sitelib}/
cp -R conf/* %{buildroot}/etc/st2reactor
install -m755 bin/st2sensorcontainer %{buildroot}/usr/bin/st2sensorcontainer
install -m755 bin/st2rulesengine %{buildroot}/usr/bin/st2rulesengine
install -m755 bin/st2-rule-tester %{buildroot}/usr/bin/st2-rule-tester

%files

/usr/lib/python2.7/site-packages/st2reactor*
/usr/bin/st2sensorcontainer
/usr/bin/st2rulesengine
/usr/bin/st2-rule-tester
/etc/st2reactor*
