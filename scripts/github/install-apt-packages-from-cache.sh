#!/usr/bin/env bash

# Special script which supports installing apt-packages, caching installes files into a directory
# and then on next run if cache is available, directly copying installed files to speed up the
# build

# Packages which will be installed and cached
APT_PACKAGES="libldap2-dev libsasl2-dev libssl-dev libyaml-dev ldap-utils"

# Directory where installed package files will be copied - should match directory specified for
# cache target in github actions workflow
CACHE_DIRECTORY="${HOME}/apt_cache"

if [[ "$CACHE_HIT" == 'true' ]]; then
    echo "Restoring cached apt packages data from ${CACHE_DIRECTORY}"
    sudo cp --force --recursive ~/apt_cache/* /
else
    echo "No cache found, installing packages using apt-get"
    # shellcheck disable=SC2086
    sudo apt-get update && sudo apt-get install -y ${APT_PACKAGES}

    mkdir -p "${CACHE_DIRECTORY}"

    for dep in ${APT_PACKAGES}; do
        echo "Caching package files for package ${dep} into ${CACHE_DIRECTORY}"
        dpkg -L "$dep" | while IFS= read -r f; do if test -f "$f"; then echo "$f"; fi; done | xargs cp --parents --target-directory "${CACHE_DIRECTORY}"
    done

    ls -la "${CACHE_DIRECTORY}"
    du -hs "${CACHE_DIRECTORY}"
fi
