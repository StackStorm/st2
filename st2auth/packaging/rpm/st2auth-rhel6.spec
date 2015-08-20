Summary: ST2 Authentication
Name: st2auth
Version: 0.4.0
Release: 1
License: Apache
Group: Applications/Engineering
BuildArch: noarch
Source: /opt/git/st2/st2auth.tar.gz
URL: https://github.com/StackStorm/st2
Vendor: StackStorm
Packager: Estee Tew <st2@stackstorm.com>
Requires:       st2common

%description
An automation plaform that needs a much better description than this.

%prep
%setup

%build
sed -i -r "s~logs~/var/log/st2~g" conf/logging.conf

%install

mkdir -p %{buildroot}/etc/st2auth
mkdir -p %{buildroot}/usr/local/lib/python2.7/site-packages/
mkdir -p %{buildroot}/usr/bin
cp -R st2auth %{buildroot}/usr/local/lib/python2.7/site-packages/
cp -R conf/* %{buildroot}/etc/st2auth
install -m755 bin/st2auth %{buildroot}/usr/bin/st2auth

%files

/usr/local/lib/python2.7/site-packages/st2auth*
/usr/bin/st2auth
/etc/st2auth*
