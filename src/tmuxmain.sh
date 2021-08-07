#!/bin/sh
if [ "$1" = "-CC" ]; then CC=-CC
elif [ "$1" = "-noCC" ]; then CC=""
elif [ "$LC_TERMINAL" = "iTerm2" ]; then CC=-CC
else CC=""
fi

exec tmux $CC new -A -s main
