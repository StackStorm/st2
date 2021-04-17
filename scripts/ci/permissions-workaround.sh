#!/usr/bin/env bash
set -e

if [ "$(whoami)" != 'root' ]; then
    echo 'Please run with sudo'
    exit 2
fi

# rabbitmq user needs access to the ssl_certs fixtures during integration tests
# stanley needs to work with packs fixtures during the packs tests
# this can't be the 'travis' user or the 'runner' user (GitHub actions user)
# because 'stanley' is the hardcoded user in the tests
# o=other; X=only set execute bit if user execute bit is set (eg on dirs)
chmod -R o+rX "${ST2_CI_REPO_PATH}/st2tests/st2tests/fixtures" "${ST2_CI_REPO_PATH}/contrib"

# make sure parent directories are traversable
d="${ST2_CI_REPO_PATH}/st2tests/st2tests"
while [[ "${d}" != "/" ]]; do
    chmod o+rx "${d}"
    d=$(dirname "${d}")
done
