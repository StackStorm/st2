#!/bin/sh

pushd $GITDIR/scripts

config=../package.meta
echo "Writing version, gitSHA and circle_build_url to: package.meta (Final location: /opt/stackstorm/st2)"
if [ -e "$config" ]; then
	rm $config
fi
touch $config
cat <<package_meta >$config
[server]
version = $(python -c 'execfile("../st2common/st2common/__init__.py"); print __version__')
git_sha = $(git rev-parse --short HEAD)
circle_build_url = $(echo $ST2_CIRCLE_URL)

package_meta

echo Contents of package.meta for reference:
cat ../package.meta
popd
