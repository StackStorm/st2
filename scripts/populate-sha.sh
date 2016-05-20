#!/bin/sh

pushd $GITDIR/scripts

echo GIT:$GITDIR
echo PWD:`pwd`
echo LS: `ls -al ../`


config=../package.meta
echo "Writing version, SHA and circle_build_url  to $config  ..."
if [ -e "$config" ]; then
	rm $config
fi
touch $config
cat <<package_meta >$config
[server]
version = $(python -c 'execfile("../st2common/st2common/__init__.py"); print __version__')
git_sha = $(git rev-parse --short HEAD)
circle_build_url=$(echo $ST2_CIRCLE_URL)
circle_build_url=$(echo $CIRCLE_BUILD_URL)

package_meta

echo Contents of package.meta:
cat ../package.meta
popd

echo env variables to find Circle CI URL
export
