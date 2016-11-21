register_runners() {
  st2ctl reload --register-runners
}

if [ "$1" -ge 1 ]; then
  register_runners
fi
