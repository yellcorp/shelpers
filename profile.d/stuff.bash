cdof()
{
	if [[ $# -ne 1 ]]; then
		echo "usage: cdof FILEPATH" 1>&2
		echo "Changes to the enclosing directory of FILEPATH" 1>&2
		return 1
	fi

	# A simplifcation COULD be to just cd to the specified directory then do
	# `cd ..`, but this will trash `cd -` to return to the previous directory
	local container="$(dirname -- "$1")"
	echo $container
	cd -- "$container"
}
