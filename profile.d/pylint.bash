__yc_pylint()
{
	local py_exec="$1"
	shift
	"$py_exec" -c 'import pylint; pylint.run_pylint()' "$@"
}

alias pylint2="__yc_pylint python"
alias pylint3="__yc_pylint python3"
