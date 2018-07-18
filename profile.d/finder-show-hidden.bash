__yc_finder_show_all()
{
	defaults write com.apple.Finder AppleShowAllFiles "$1" && \
		killall Finder
}

alias finder-show-hidden="__yc_finder_show_all YES"
alias finder-hide-hidden="__yc_finder_show_all NO"
