__yc_err()
{
	echo "$@" 1>&2
}

__yc_usage()
{
	__yc_err usage: "$(basename -- "$0")" "$@"
}

__yc_die_usage()
{
	__yc_usage "$@"
	exit 1
}

__yc_die()
{
	__yc_err "$@"
	exit $1
}
