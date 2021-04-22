#!/usr/bin/env bash
set -e

# Note: Use the verison of virtualenv pinned in fixed-requirements.txt so we
#       only have to update it one place when we change the version
# Note: Use --user to avoid polluting system site-packages (which breaks one of our tests)
# TODO: simplify this once fixed in contrib/runners/python_runner/tests/integration/test_pythonrunner_behavior.py
if [[ ! -f ~/virtualenv/bin/virtualenv ]]; then  # use the cached version whenever possible
  pip install --user --upgrade --force-reinstall "$(grep "^virtualenv" fixed-requirements.txt)"
  virtualenv --no-download ~/virtualenv
  ~/virtualenv/bin/pip install --upgrade --force-reinstall "$(grep "^virtualenv" fixed-requirements.txt)"
  # drop the --user install virtualenv to prevent polluting tests
  pip freeze --user | xargs pip uninstall -y
fi

mkdir -p ~/.local/bin
ln -s ~/virtualenv/bin/virtualenv ~/.local/bin/virtualenv

command -v virtualenv
virtualenv --version
