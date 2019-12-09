# tmux
trapHandler () {
	trap SIGINT
	if ! [ -z "$TMUX" ]; then
		tmux select-pane -P 'bg=default' \; select-pane -P 'fg=default'
	fi 
}

tssh () {
	trap "trapHandler" INT
	command ssh "$@"
	if ! [ -z "$TMUX" ]; then
		tmux select-pane -P 'bg=default' \; select-pane -P 'fg=default'
	fi 
}
