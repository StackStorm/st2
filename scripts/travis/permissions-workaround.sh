#!/usr/bin/env bash
set -e

if [ "$(whoami)" != 'root' ]; then
    echo 'Please run with sudo'
    exit 2
fi

# stanley needs to work with some fixtures during the tests
# this can't be the travis user because 'stanley' is the hardcoded user in the tests
# o=other; X=only set execute bit if user execute bit is set (eg on dirs)
chmod -R o+rwX ${TRAVIS_BUILD_DIR}/StackStorm/st2/st2tests/st2tests/fixtures/packs
