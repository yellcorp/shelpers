cdof()
{
	if [[ $# -ne 1 ]]; then
		echo "usage: cdof FILEPATH" 1>&2
		echo "Changes to the enclosing directory of FILEPATH" 1>&2
		return 1
	fi

	# A simplification COULD be to just cd to the specified directory then do
	# `cd ..`, but this will trash `cd -` to return to the previous directory
	local container="$(dirname -- "$1")"
	echo $container
	cd -- "$container"
}

gox64()
{
	local current="$(/usr/bin/arch)"
	case "$current" in
		i386|x86_64|x86_64h)
			echo "$0: Already running Intel (arch=$current)" 1>&2
			return 1
			;;
		*)
			/usr/bin/arch -x86_64 "$SHELL"
			;;
	esac
}

pipenv()
{
	echo 'pipenv: Use poetry instead'
	echo '  Or remove this reminder for the current shell session with'
	echo '  `unset -f pipenv`'
	return 1
}

poetry-activate()
{
  eval "$(poetry env activate)"
}
