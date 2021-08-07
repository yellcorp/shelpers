#!/bin/sh

MYNAME="$(basename -- "$0")"
case "$MYNAME" in
  finder-show-hidden)
    VALUE=YES
    ;;
  finder-hide-hidden)
    VALUE=NO
    ;;
  *)
    VALUE="$1"
    case "$1" in
      YES|yes)
        VALUE=YES
        ;;
      NO|no)
        VALUE=NO
        ;;
      *)
        echo "usage: $MYNAME YES|NO" 1>&2
        exit 1
        ;;
    esac
    ;;
esac

defaults write com.apple.Finder AppleShowAllFiles -boolean "$VALUE" && \
  pkill -TERM -P 1 -f -t - '/Finder.app/Contents/MacOS/Finder'
