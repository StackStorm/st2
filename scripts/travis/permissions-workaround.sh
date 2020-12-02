#!/usr/bin/env bash
set -e

if [ "$(whoami)" != 'root' ]; then
    echo 'Please run with sudo'
    exit 2
fi

# rabbitmq user needs access to the ssl_certs fixtures during integration tests
# stanley needs to work with packs fixtures during the packs tests
# this can't be the travis user because 'stanley' is the hardcoded user in the tests
# o=other; X=only set execute bit if user execute bit is set (eg on dirs)
chmod -R o+rX ${GITHUB_WORKSPACE}/st2tests/st2tests/fixtures ${GITHUB_WORKSPACE}/contrib

# make sure parent directories are traversable
d=${GITHUB_WORKSPACE}/st2tests/st2tests
while [[ "${d}" != "/" ]]; do
    chmod o+rx "${d}"
    d=$(dirname "${d}")
done
