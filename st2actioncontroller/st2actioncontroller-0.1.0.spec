Summary: Stanley Action Controller
Name: st2actioncontroller
Version: 0.1.0
Release: 1
License: license
Group: Applications/Engineering
Source: /opt/git/stanley/st2actioncontroller-0.1.0.tar.gz
URL: https://github.com/StackStorm/stanley
Vendor: StackStorm
Packager: Stormin Stanley <stanley@stackstorm.com>
Requires:       st2common

%description
An automation plaform that needs a much better description than this.

%prep
%setup

%build

%install

mkdir -p %{buildroot}/etc/st2actioncontroller
mkdir -p %{buildroot}%{python2_sitelib}
mkdir -p %{buildroot}/usr/bin/
cp -R st2actioncontroller %{buildroot}%{python2_sitelib}/
cp -R conf/* %{buildroot}/etc/st2actioncontroller
install -m755 bin/action_controller %{buildroot}/usr/bin/action_controller

%files

/usr/lib/python2.7/site-packages/st2actioncontroller*
/usr/bin/action_controller
/etc/st2actioncontroller*
