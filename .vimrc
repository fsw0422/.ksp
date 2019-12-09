" settings
syntax on

set encoding=utf-8
set backspace=indent,eol,start
set autochdir
set mouse=a
set hlsearch
set incsearch
set number
set completeopt=longest,menuone,preview
set background=dark
set pastetoggle=<f6>
set visualbell
set noerrorbells

" key maps
"" general maps
nmap <f4> :se nu!<cr>
nmap <f5> :se hls!<cr>

"" copy / paste maps
vmap <c-c> "+yi
vmap <c-x> "+c
vmap <c-v> c<esc>"+p
imap <c-v> <C-r><C-o>+

" terminal
highlight Pmenusel ctermfg=White ctermbg=Blue cterm=Bold

"" when editing a file, always jump to the last cursor position
autocmd BufReadPost *
	\ if line("'\"") > 0 && line ("'\"") <= line("$") |
	\	 exe "normal! g'\"" |
	\ endif

"" additional window
autocmd CursorMovedI * if pumvisible() == 0 | pclose | endif
autocmd InsertLeave  * if pumvisible() == 0 | pclose | endif

"" don't wake up system with blinking cursor:
let &guicursor = &guicursor . ",a:blinkon0"
