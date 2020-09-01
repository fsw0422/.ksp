" Vundle setup
set nocompatible
filetype off
set runtimepath+=~/.ksp/
call vundle#begin()

"" setup plugins
Plugin 'scrooloose/nerdtree.git'
Plugin 'kien/ctrlp.vim.git'
Plugin 'ervandew/supertab.git'
Plugin 'vim-scripts/AutoComplPop.git'
Plugin 'majutsushi/tagbar.git'
Plugin 'davidhalter/jedi-vim.git'

"" plugin settings
let NERDTreeShowHidden = 1
let g:ctrlp_show_hidden = 1
let g:SuperTabCrMapping = 1
let g:SuperTabDefaultCompletionType = '<c-x><c-o>'
let g:acp_behaviorKeywordLength = 2
let g:acp_completeoptPreview = 1
let g:acp_behaviorPythonOmniLength = -1
let g:jedi#force_py_version = 3

" Key maps
"" general maps
nmap <f12> :q!<cr>

"" copy / paste maps
vmap <c-c> "+yi
vmap <c-x> "+c
vmap <c-v> c<esc>"+p
imap <c-v> <C-r><C-o>+

"" leader maps
let maplocalleader = ','
nmap <Localleader>n :NERDTreeToggle<cr>
nmap <LocalLeader>t :TagbarToggle<cr>
autocmd FileType python nmap <buffer><LocalLeader>c :exe 'silent !ctags -R --fields=+l --languages=python --python-kinds=-iv -f ./.tags ./'<cr>:redraw!<cr>

" Global settings
"" general
call vundle#end()
filetype plugin indent on
syntax on
highlight Pmenusel ctermfg=White ctermbg=Blue cterm=Bold

set autochdir
set backspace=indent,eol,start
set background=dark
set completeopt=longest,menuone,preview
set encoding=utf-8
set history=50 " keep 50 lines of command line history
set hlsearch
set incsearch
set mouse=a
set noerrorbells
set number
set pastetoggle=<f6>
set ruler " show the cursor position all the time
set tags=./tags,tags; " load ctags db
set visualbell

"" operation depending on filetype
autocmd Filetype python set tabstop=4 | set shiftwidth=4 | set expandtab | retab

"" terminal
""" when editing a file, always jump to the last cursor position
autocmd BufReadPost *
	\ if line("'\"") > 0 && line ("'\"") <= line("$") |
	\	 exe "normal! g'\"" |
	\ endif

""" additional window
autocmd CursorMovedI * if pumvisible() == 0 | pclose | endif
autocmd InsertLeave  * if pumvisible() == 0 | pclose | endif

""" don't wake up system with blinking cursor:
let &guicursor = &guicursor . ",a:blinkon0"
