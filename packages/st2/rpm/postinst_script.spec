register_runners() {
  st2ctl reload --register-runners --register-fail-on-failure
}

if [ "$1" -ge 1 ]; then
  register_runners
fi
