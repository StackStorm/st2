#!/usr/bin/env bash
# shellcheck disable=SC2317  # We have exit 0 to purposely skip the remainder of the file.
set -e

# Special script which supports installing apt-packages, caching installed files into a directory
# and then on next run if cache is available, re-using that cache

BASE_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
APT_PACKAGES_FILE_PATH="${BASE_DIR}/apt-packages.txt"

# Packages which will be installed and cached
# NOTE: shellcheck is already available in docker runner image we use
# shellcheck disable=SC2002
APT_PACKAGES=$(cat "${APT_PACKAGES_FILE_PATH}" | tr -d "\n")

echo "Installing apt packages: ${APT_PACKAGES}"
echo ""
echo "CACHE_HIT=${CACHE_HIT}"
echo ""

# TODO: Recently using cached dependency started failing so I (@Kami) temporary disabled cache.
# We should investigate why it's failing and try to fix it.
sudo apt-get -y update
# shellcheck disable=SC2086
sudo apt-get -f -y --reinstall install ${APT_PACKAGES}
sudo dpkg -l
exit 0

# Directory where installed package files will be copied - should match directory specified for
# cache target in github actions workflow
CACHE_DIRECTORY="${HOME}/apt_cache"

export APT_DIR="${CACHE_DIRECTORY}"
export APT_STATE_LISTS="${APT_DIR}/lists"
export APT_CACHE_ARCHIVES="${APT_DIR}/archives"

# shellcheck disable=SC2059
printf "dir::state::lists    ${APT_STATE_LISTS};\ndir::cache::archives    ${APT_CACHE_ARCHIVES};\n" | sudo tee /etc/apt/apt.conf

mkdir -p "${APT_STATE_LISTS}/partial"
mkdir -p "${APT_CACHE_ARCHIVES}/partial"

# NOTE apt-get update is only needed is there is no cache. If there is an existing cache, we don't
# run it to speed things up
if [[ "$CACHE_HIT" != 'true' ]]; then
    sudo apt-get -y update
fi

# shellcheck disable=SC2086
sudo apt-get -f -y --reinstall install ${APT_PACKAGES}

ls -la "${APT_STATE_LISTS}"
ls -la "${APT_CACHE_ARCHIVES}"

# Workaround for caching issue (ensure runer can read the downloaded packages)
sudo chown -R runner:runner "${CACHE_DIRECTORY}"
