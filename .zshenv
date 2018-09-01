# tmux
trapHandler () { trap SIGINT; tmux select-pane -P 'bg=default' \; select-pane -P 'fg=default'; }
ssh () { trap "trapHandler" INT; command ssh "$@"; tmux select-pane -P 'bg=default' \; select-pane -P 'fg=default'; }
