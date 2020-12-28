" Vundle setup
set nocompatible
filetype off
set runtimepath+=~/.ksp/
call vundle#begin()

"" setup plugins
Plugin 'scrooloose/nerdtree.git'
Plugin 'kien/ctrlp.vim.git'
Plugin 'vim-scripts/AutoComplPop.git'
Plugin 'davidhalter/jedi-vim.git'
Plugin 'tpope/vim-markdown'

"" plugin settings
let g:NERDTreeShowHidden = 1
let g:ctrlp_show_hidden = 1
let g:acp_behaviorKeywordLength = 2
let g:acp_completeoptPreview = 1
let g:acp_behaviorPythonOmniLength = -1
let g:markdown_fenced_languages = ['java', 'python', 'bash=sh']
let g:jedi#force_py_version = 3
let g:jedi#goto_assignments_command = "<C-w>a"
let g:jedi#goto_command = "<C-w>c"
let g:jedi#goto_definitions_command = "<C-w>d"
let g:jedi#goto_stubs_command = "<C-w>s"
let g:jedi#documentation_command = "<C-w>D"
let g:jedi#usages_command = "<C-w>u"
let g:jedi#rename_command = "<C-w>r"

" Key maps
"" custom maps
nmap <f12> :q!<cr>
nmap <C-x> <C-^><cr>
nmap <C-w>n :NERDTreeToggle<cr>
nmap <C-w>rr :CtrlPClearCache<cr> :NERDTreeFocus<cr>R<C-w><C-p>
nmap <C-w>R :so $MYVIMRC<cr>

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
autocmd filetype python set tabstop=4 | set shiftwidth=4 | set expandtab | retab

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
