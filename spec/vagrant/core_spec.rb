require 'spec_helper'

# Install Packages onto Operating System

## Dev Build Packages Requirements
BUILD_DEBIAN_PACKAGES = %w(make python-virtualenv python-dev realpath gdebi-core
                         python-pip libssl-dev libyaml-dev libffi-dev libxml2-dev
                         libxslt1-dev python-dev gcc git libmysqlclient-dev)
BUILD_REDHAT_PACKAGES = %w(python-pip python-virtualenv python-devel gcc-c++ git-all
                         openssl-devel libyaml-devel libffi-devel libxml2-devel libxslt-devel
                         python-devel mailcap redhat-rpm-config mysql-devel)

BUILD_DEBIAN_PACKAGES.each do |package|
  describe package(package), :if => os[:family] == 'ubuntu' do
    it { should be_installed }
  end
end

BUILD_REDHAT_PACKAGES.each do |package|
  describe package(package), :if => os[:family] == 'redhat' do
    it { should be_installed }
  end
end

## StackStorm Package Installation
ST2_PACKAGES = %w(st2common st2reactor st2actions st2api st2auth st2debug)
ST2_DEBIAN_PACKAGES = %w(python-st2client)
ST2_REDHAT_PACKAGES = %w(st2client)

# APT Package Repository
describe file('/etc/apt/sources.list.d/stackstorm.list'), :if => os[:family] == 'ubuntu' do
  it { should be_file }
  it { should contain 'deb https://downloads.stackstorm.net/deb/' }
end

[ST2_PACKAGES, ST2_DEBIAN_PACKAGES].flatten.each do |package|
  describe package(package), :if => os[:family] == 'ubuntu' do
    it { should be_installed }
  end
end

# YUM Package Repository
describe file('/etc/yum.repos.d/stackstorm.repo'), :if => os[:family] == 'redhat' do
  it { should be_file }
  it { should contain 'baseurl=https://downloads.stackstorm.net/rpm/fedora/20/deps/' }
end

[ST2_PACKAGES, ST2_REDHAT_PACKAGES].flatten.each do |package|
  describe package(package), :if => os[:family] == 'redhat' do
    it { should be_installed }
  end
end

# Check version of Python is supported version
describe command('python --version') do
  its(:stdout) { should match /Python 2\.7\./ }
end

# MongoDB
MONGODB_DEBIAN_PACKAGES = %w(mongodb-server)
MONGODB_REDHAT_PACKAGES = %w(mongo mongodb-server)

MONGODB_REDHAT_PACKAGES.each do |package|
  describe package(package), :if => os[:family] == 'redhat' do
    it { should be_installed }
  end
end

MONGODB_DEBIAN_PACKAGES.each do |package|
  describe package(package), :if => os[:family] == 'ubuntu' do
    it { should be_installed }
  end
end

describe service('mongodb') do
  it { should be_enabled }
  it { should be_running }
end

# RabbitMQ
RABBITMQ_DEBIAN_PACKAGES = %w(rabbitmq-server)
RABBITMQ_REDHAT_PACKAGES = %w(rabbitmq-servers)

RABBITMQ_REDHAT_PACKAGES.each do |package|
  describe package(package), :if => os[:family] == 'redhat' do
    it { should be_installed }
  end
end

RABBITMQ_DEBIAN_PACKAGES.each do |package|
  describe package(package), :if => os[:family] == 'ubuntu' do
    it { should be_installed }
  end
end

describe service('rabbitmq') do
  it { should be_enabled }
  it { should be_running }
end

describe file('/usr/bin/rabbitmqadmin') do
  it { should be_file }
  it { should be_executable }
end

describe port(5672) do
  it { should be_listening }
end

# Features
## Authentication
describe file('/etc/st2/st2.conf') do
  it { should contain 'mode = standalone' }
  it { should contain 'backend_kwargs = {"file_path": "/etc/st2/htpasswd"}' }
end

describe file('/etc/st2/htpasswd') do
  it { should be_file }
  it { should contain 'testu:{SHA}V1t6eZLxnehb7CTBuj61Nq3lIh4=' }
end

## Windows Support
WIN_DEBIAN_PACKAGES = %w(smbclient winexe)
WIN_REDHAT_PACKAGES = %w(samba-client winexe)

WIN_REDHAT_PACKAGES.each do |package|
  describe package(package), :if => os[:family] == 'redhat' do
    it { should be_installed }
  end
end

WIN_DEBIAN_PACKAGES.each do |package|
  describe package(package), :if => os[:family] == 'ubuntu' do
    it { should be_installed }
  end
end

# Common Setup
## User setup
describe user('stanley') do
  it { should exist }
  it { should have_home_directory '/home/stanley' }
end

## Python Setup
describe command('pip list') do
  its(:stdout) { should match /APscheduler (3.0.3)/ }
#   }
#   #   should match /eventlet (0.17.3)/
#   #   should match /Flask (0.10.1)/
#   #   should match /FlaskJsonSchema (0.1.1)/
#   #   should match /GitPython (0.3.2.1)/
#   #   should match /Jinja2 (2.7.3)/
#   #   should match /jsonschema (2.4.0)/
#   #   should match /kombu (3.0.26)/
#   #   should match /mongoengine (0.8.8)/
#   #   should match /oslo.config (1.11.0)/
#   #   should match /paramiko (1.15.2)/
#   #   should match /pecan (0.7.0)/
#   #   should match /pymongo (2.8)/
# 
#     ## These still need to be codified
#     # python-dateutil
#     # python-json-logger
#     # pyyaml
#     # requests
#     # setuptools==11.1
#     # six==1.9.0
#     # git+https://github.com/StackStorm/python-mistralclient.git@st2-0.9.0
#     # git+https://github.com/StackStorm/fabric.git@stanley-patched
#     # passlib>=1.6.2,<1.7
#     # lockfile>=0.10.2,<0.11
#     # python-gnupg>=0.3.7,<0.4
#     # jsonpath-rw>=1.3.0
#     # # Requirements for linux pack
#     # # used by file watcher sensor
#     # pyinotify>=0.9.5,<=0.10
#     # -e git+https://github.com/Kami/logshipper.git@stackstorm_patched#egg=logshipper
#     # # used by nmap actions
#     # python-nmap>=0.3.4,<0.4
end

## Sudoers Setup
# commented out because there is a clear descrepency between puppet/st2_deploy.sh
#describe file('/etc/sudoers/st2') do
#  its(:content) { should contain /^stanley\s+ALL=(ALL)\s+NOPASSWD: ALL/ }
#end

## Logging Setup
describe file('/var/log/st2') do
  it { should be_directory }
end

# mistral
MISTRAL_DEBIAN_PACKAGES = %w(mysql-server)
MISTRAL_REDHAT_PACKAGES = %w(mariadb mariadb-libs mariadb-devel mariadb-server)

MISTRAL_DEBIAN_PACKAGES.each do |package|
  describe package(package), :if => os[:family] == 'ubuntu' do
    it { should be_installed }
  end
end

MISTRAL_REDHAT_PACKAGES.each do |package|
  describe package(package), :if => os[:family] == 'redhat' do
    it { should be_installed }
  end
end

# describe connection string in config
# ensure mysql is setup with mistral

describe file('/opt/openstack/mistral') do
  it { should be_directory }
end

describe file('/opt/openstack/mistral/.git') do
  it { should be_directory }
end

describe file('/opt/openstack/mistral/.venv') do
  it { should be_directory }
end

describe file('/etc/mistral/mistral.conf') do
  it { should be_file }
  it { should contain 'connection = mysql://mistral:StackStorm@localhost/mistral' }
  it { should contain 'max_pool_size = 100' }
  it { should contain 'auth_enable = false' }
end

MISTRAL_INIT_COMMAND="/opt/openstack/mistral/.venv/bin/python /opt/openstack/mistral/mistral/cmd/launch.py --config-file /etc/mistral/mistral.conf --log-file /var/log/mistral.log --log-config-append /etc/mistral/wf_trace_logging.conf"

describe file('/etc/mistral/wf_trace_logging.conf') do
  it { should be_file }
  it { should contain 'args=("/var/log/mistral_wf_trace.log",)' }
end

describe file('/etc/init/mistral.conf'), :if => os[:family] == 'ubuntu' do
  it { should be_file }
  it { should contain MISTRAL_INIT_COMMAND }
end

describe file('/etc/systemd/system/mistral.service'), :if => os[:family] == 'redhat' do
  it { should be_file }
  it { should contain MISTRAL_INIT_COMMAND }
end

describe file('/etc/mistral/actions/st2mistral') do
  it { should be_directory }
end

describe file('/etc/mistral/actions/st2mistral/.git') do
  it { should be_directory }
end

describe port(8989) do
  it { should be_listening }
end

# st2api
describe port(9101) do
  it { should be_listening }
end

# TODO: This needs an init script
describe service('st2api') do
  # it { should be_enabled }
  # it { should be_running }
end

describe command('ps ax') do
  its(:stdout) { should match /st2api/ }
end

# st2auth
describe port(9100) do
  it { should be_listening }
end

# TODO: This needs an init script
describe service('st2auth') do
  # it { should be_enabled }
  # it { should be_running }
end

describe command('ps ax') do
  its(:stdout) { should match /st2auth/ }
end

describe command('st2 auth testu -p testu') do
  its(:exit_status) { should eq 0 }
  its(:stdout) { should match /token/ }
end

# actionrunner
# TODO: This needs an init script
describe service('st2actionrunner') do
  # it { should be_enabled }
  # it { should be_running }
end

describe command('ps ax') do
  its(:stdout) { should match /st2actionrunner/ }
end

# notifier
# TODO: This needs an init script
describe service('st2notifier') do
  # it { should be_enabled }
  # it { should be_running }
end

describe command('ps ax') do
  its(:stdout) { should match /st2notifier/ }
end

# rules engine
# TODO: This needs an init script
describe service('st2rulesengine') do
  # it { should be_enabled }
  # it { should be_running }
end

describe command('ps ax') do
  its(:stdout) { should match /st2rulesengine/ }
end

# sensor container
# TODO: This needs an init script
describe service('st2sensorcontainer') do
  # it { should be_enabled }
  # it { should be_running }
end

describe command('ps ax') do
  its(:stdout) { should match /st2sensorcontainer/ }
end

# results tracker
# TODO: This needs an init script
describe service('st2resultstracker') do
  # it { should be_enabled }
  # it { should be_running }
end

describe command('ps ax') do
  its(:stdout) { should match /st2resultstracker/ }
end

# st2web
WEBUI_CONFIG_PATH='/opt/stackstorm/static/webui/config.js'
AUTH_FILE_PATH='/etc/st2/htpasswd'

describe file(WEBUI_CONFIG_PATH) do
  it { should be_file }
  it { should contain "name: 'StackStorm'" }
  it { should contain "url: '//:9101'" }
  it { should contain "auth: '//:9100'" }
end

describe port(8080) do
  it { should be_listening }
end

# TODO: This needs an init script
describe service('st2web') do
  # it { should be_enabled }
  # it { should be_running }
end

describe command('ps ax') do
  its(:stdout) { should match /SimpleHTTPServer/ }
end

# st2client
describe file('/usr/bin/st2') do
  it { should be_file }
  it { should be_executable }
end

describe command('pip list') do
  its(:stdout) { should match /APscheduler (3.0.3)/ }
end

# prettytable
# pyyaml
# requests
# six
# python-dateutil
# jsonpath-rw
