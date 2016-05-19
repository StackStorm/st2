#!/bin/sh

pushd $GITDIR/scripts

echo GIT:$GITDIR
echo PWD:`pwd`
echo LS: `ls -al ../`


config=../package.meta
echo "Writing Version and SHA info. to $config"
if [ -e "$config" ]; then
	rm $config
fi
touch $config
cat <<package_meta >$config
[server]
version = $(python -c 'execfile("../st2common/st2common/__init__.py"); print __version__')
git_sha = $(git rev-parse --short HEAD)
package_meta

popd
echo Contents of package.meta:
cat ../package.meta

echo Export variables to find Circle CI URL

export
