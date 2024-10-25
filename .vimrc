" Vundle setup
set nocompatible
filetype off
set runtimepath+=~/.ksp/
call vundle#begin()

"" setup plugins
Plugin 'scrooloose/nerdtree.git'
Plugin 'nvie/vim-flake8.git'
Plugin 'kien/ctrlp.vim.git'
Plugin 'vim-scripts/AutoComplPop.git'
Plugin 'davidhalter/jedi-vim.git'
Plugin 'tpope/vim-markdown'
Plugin 'weirongxu/plantuml-previewer.vim'
Plugin 'aklt/plantuml-syntax'
Plugin 'tyru/open-browser.vim'

"" plugin settings
let g:NERDTreeRespectWildIgnore=1
let g:NERDTreeShowHidden=1
let g:ctrlp_show_hidden = 1
let g:acp_behaviorKeywordLength = 2
let g:acp_completeoptPreview = 1
let g:acp_behaviorPythonOmniLength = -1
let g:jedi#force_py_version = 3
let g:jedi#goto_definitions_command = "gi"
let g:jedi#goto_stubs_command = "gs"
let g:jedi#usages_command = "fu"

"Key maps
"" custom maps
nmap <f1> :NERDTreeToggle<cr>
nmap <f2> :PlantumlOpen<cr>
nmap <f3> :PlantumlSave<cr>
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

"" operation depending on filetype
autocmd BufWritePre * :%s/\s\+$//e
autocmd FileType python set tabstop=4 | set shiftwidth=4 | set expandtab | retab
autocmd BufWritePost *.py call flake8#Flake8()

"" terminal
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
