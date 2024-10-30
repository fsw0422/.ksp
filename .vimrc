" Vundle setup
set nocompatible
filetype off
set runtimepath+=~/.ksp/
call vundle#begin()

"" setup plugins
Plugin 'scrooloose/nerdtree.git'
Plugin 'kien/ctrlp.vim.git'
Plugin 'vim-scripts/AutoComplPop.git'
Plugin 'tyru/open-browser.vim'

"" plugin settings
let g:NERDTreeRespectWildIgnore=1
let g:NERDTreeShowHidden=1
let g:ctrlp_show_hidden = 1
let g:acp_behaviorKeywordLength = 2
let g:acp_completeoptPreview = 1

"Key maps
"" custom maps
nmap <f1> :NERDTreeToggle<cr>
nmap <f12> :q!<cr>
nmap <c-h> <c-o><cr>
nmap <c-l> <c-i><cr>
nmap <c-x> :e#<cr>
nmap <c-g>c :!lazygit<cr>
nmap <c-r>r :CtrlPClearCache<cr> :NERDTreeFocus<cr>R<c-w><c-p>
nmap <c-r>R :so $MYVIMRC<cr>
nmap <c-a> :NERDTreeFind<cr>

" Global settings
"" general
call vundle#end()
filetype plugin indent on
syntax on
highlight Pmenusel ctermfg=White ctermbg=Blue cterm=Bold

set autochdir
set backspace=indent,eol,start
set background=dark
set clipboard^=unnamed,unnamedplus
set completeopt=longest,menuone,preview
set encoding=utf-8
set hidden
set hlsearch
set incsearch
set mouse=a
set noerrorbells
set number
set ruler
set visualbell
set wildignore+=*.pyc,*.o,*.obj,*.svn,*.swp,*.class,*.hg,*.DS_Store,*.min.*

"" terminal
""" remove trailing whitspaces for each line on write
autocmd BufWritePre * :%s/\s\+$//e

""" when editing a file, always jump to the last cursor position
autocmd BufReadPost *
	\ if line("'\"") > 0 && line ("'\"") <= line("$") |
	\	 execute "normal! g'\"" |
	\ endif

""" additional window
autocmd CursorMovedI * if pumvisible() == 0 | pclose | endif
autocmd InsertLeave  * if pumvisible() == 0 | pclose | endif

""" don't wake up system with blinking cursor:
let &guicursor = &guicursor . ",a:blinkon0"
