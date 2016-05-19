#!/bin/sh

git_sha=$(git rev-parse --short HEAD)
version=$(cat ../st2common/st2common/__init__.py | grep __version__ | sed -r '1!d;s/.*=\s+//'| tr -d "'")

config=../package.meta
echo "Writing Version and SHA info. to $config"
if [ -e "$config" ]; then
	rm $config
fi
touch $config
cat <<package_meta >$config
[server]
version = $version
git_sha = $git_sha
package_meta
