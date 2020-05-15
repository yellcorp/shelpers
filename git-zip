#!/bin/sh


TIMESTAMP_FORMAT='%Y%m%d%H%M%S'
HASH_CHARS=8

TOPLEVEL="$(git rev-parse --show-toplevel)"
if [ -z "$TOPLEVEL" ]; then
	git --version && \
		echo Are you in a git repository? || \
		echo Is Git installed?
	exit 1
fi

cd "$TOPLEVEL" || exit 1

BASENAME="$(basename -- "$TOPLEVEL")"
TIMESTAMP="$(date +"$TIMESTAMP_FORMAT")"
HASH="$(git rev-parse --short=$HASH_CHARS HEAD)"
if [ -z "$HASH" ]; then
	exit 1
fi

ARCHIVENAME="$BASENAME-$TIMESTAMP-$HASH"
MYNAME="$(basename -- "$0")"
case "$MYNAME" in
	git-tgz)
		export GZIP=-9
		git ls-files | tar -T - -nczvf "$ARCHIVENAME.tar.gz"
		;;
	git-tbz)
		git ls-files | tar -T - -ncjvf "$ARCHIVENAME.tar.bz2"
		;;
	*)
		if [ "$MYNAME" != "git-zip" ]; then
			echo "Don't know what format to make, so zip it is" 1>&2
		fi
		git ls-files | zip -9 -@ "$ARCHIVENAME.zip"
		;;
esac
