cdof()
{
	if [[ $# -ne 1 ]]; then
		__yc_err usage: cdof FILEPATH
		return 1
	fi
	cd -- "$(dirname -- "$1")"
}

alias reveal='open -R'
