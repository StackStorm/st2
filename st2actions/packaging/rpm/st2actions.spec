Summary: ST2 Actions
Name: st2actions
Version: 0.4.0
Release: 1
License: Apache
Group: Applications/Engineering
BuildArch: noarch
Source: /opt/git/st2/st2actions.tar.gz
URL: https://github.com/StackStorm/st2
Vendor: StackStorm
Packager: Estee Tew <st2@stackstorm.com>
Requires:     st2common

%description
An automation plaform that needs a much better description than this.

%prep
%setup

%build
sed -i -r "s~logs~/var/log/st2~g" conf/*log*.conf

%install

mkdir -p %{buildroot}/etc/st2actions
mkdir -p %{buildroot}%{python2_sitelib}
mkdir -p %{buildroot}/usr/bin
cp -R st2actions %{buildroot}%{python2_sitelib}/
cp -R bin %{buildroot}%{python2_sitelib}/st2actions/
cp -R conf/* %{buildroot}/etc/st2actions
install -m755 bin/st2actionrunner %{buildroot}/usr/bin/st2actionrunner
install -m755 bin/st2resultstracker %{buildroot}/usr/bin/st2resultstracker
install -m755 bin/st2notifier %{buildroot}/usr/bin/st2notifier
%files

/usr/lib/python2.7/site-packages/st2actions*
/usr/bin/st2actionrunner
/usr/bin/st2resultstracker
/usr/bin/st2notifier
/etc/st2actions*
