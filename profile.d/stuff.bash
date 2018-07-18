myip()
{
	curl "$@" http://ipinfo.io/ip
}

cdof()
{
	if [[ $# -ne 1 ]]; then
		__yc_err usage: cdof FILEPATH
		return 1
	fi
	cd -- "$(dirname -- "$1")"
}

alias    gpersp='open -b net.sourceforge.grandperspectiv'
alias       hex='open -b com.suavetech.0xED'
alias photoshop='open -b com.adobe.Photoshop'
alias     stree='open -b com.torusknot.SourceTreeNotMAS'
alias       vlc='open -b org.videolan.vlc'

alias reveal='open -R'
