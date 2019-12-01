" Key maps
"" general maps
nmap <f4> :se nu!<cr>
nmap <f5> :se hls!<cr>

"" copy / paste maps
vmap <c-c> "+yi
vmap <c-x> "+c
vmap <c-v> c<esc>"+p
imap <c-v> <C-r><C-o>+

" Settings
hi Pmenusel ctermfg=White ctermbg=Blue cterm=Bold

se enc=utf-8
se tags=./tags,tags; " load ctags db
se bs=indent,eol,start
se hi=50 " keep 50 lines of command line history
se ru " show the cursor position all the time
se acd
se mouse=a
se hls
se is
se nu
se cot=longest,menuone,preview
se bg=dark
se pt=<f6>
se vb
se noeb

"" terminal
""" when editing a file, always jump to the last cursor position
au BufReadPost *
	\ if line("'\"") > 0 && line ("'\"") <= line("$") |
	\	 exe "normal! g'\"" |
	\ endif

""" additional window
au CursorMovedI * if pumvisible() == 0 | pclose | endif
au InsertLeave  * if pumvisible() == 0 | pclose | endif

""" don't wake up system with blinking cursor:
let &guicursor = &guicursor . ",a:blinkon0"
