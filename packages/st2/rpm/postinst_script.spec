register_runners() {
  st2ctl reload --register-runners --register-fail-on-failure
}

install_orchestra_runner() {
    echo "Installing orchestra runner"
    (cd /opt/stackstorm/runners/orchestra_runner; /opt/stackstorm/virtualenv/python setup.py install)
}

if [ "$1" -ge 1 ]; then
  install_orchestra_runner
  register_runners
fi
