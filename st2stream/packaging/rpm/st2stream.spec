Summary: ST2 Stream API
Name: st2stream
Version: 0.4.0
Release: 1
License: Apache
Group: Applications/Engineering
BuildArch: noarch
Source: /opt/git/st2/st2stream.tar.gz
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

mkdir -p %{buildroot}/etc/st2stream
mkdir -p %{buildroot}%{python2_sitelib}
mkdir -p %{buildroot}/usr/bin
cp -R st2stream %{buildroot}%{python2_sitelib}/
cp -R conf/* %{buildroot}/etc/st2stream
install -m755 bin/st2stream %{buildroot}/usr/bin/st2stream

%files

/usr/lib/python2.7/site-packages/st2stream*
/usr/bin/st2stream
/etc/st2stream*
