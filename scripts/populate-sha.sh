#!/bin/sh

git_sha=$(git rev-parse --short HEAD)
version=$(cat ../st2common/st2common/__init__.py | grep __version__ | sed -r '1!d;s/.*=\s+//'| tr -d "'")

echo $version\_SHA_$git_sha

exec 3>&1 >package_meta.conf

echo "[server]"
echo "# Server version and SHA for the build"
echo "version = $version"
echo "git_sha = $git_sha"

exec >&3

