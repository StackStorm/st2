Summary: Stanley Action Runner Controller
Name: st2actionrunnercontroller
Version: 0.1.0
Release: 1
License: license
Group: Applications/Engineering
Source: /opt/git/stanley/st2actionrunnercontroller-0.1.0.tar.gz
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

mkdir -p %{buildroot}/etc/st2actionrunnercontroller
mkdir -p %{buildroot}%{python2_sitelib}
mkdir -p %{buildroot}/usr/bin
cp -R st2actionrunnercontroller %{buildroot}%{python2_sitelib}/
cp -R st2actionrunner %{buildroot}%{python2_sitelib}/
cp -R conf/* %{buildroot}/etc/st2actionrunnercontroller
install -m755 bin/actionrunner_controller %{buildroot}/usr/bin/actionrunner_controller

%files

/usr/lib/python2.7/site-packages/st2actionrunner*
/usr/bin/actionrunner_controller
/etc/st2actionrunnercontroller*
