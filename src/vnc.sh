#!/bin/sh
if [ "$#" -ne 1 ]; then
  echo "Usage: $(basename "$0") [USER@]HOST[:PORT]" >&2
  exit 1
fi

exec open "vnc://$1"
