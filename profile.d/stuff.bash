cdof()
{
	if [[ $# -ne 1 ]]; then
		echo "usage: cdof FILEPATH" 1>&2
		echo "Changes to the enclosing directory of FILEPATH" 1>&2
		return 1
	fi
	cd -- "$(dirname -- "$1")"
}
