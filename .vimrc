" Vundle setup
set nocompatible
filetype off
set runtimepath+=~/.ksp/
call vundle#begin()

let maplocalleader=','

"" setup plugins
Plugin 'scrooloose/nerdtree.git'
Plugin 'kien/ctrlp.vim.git'
Plugin 'vim-scripts/AutoComplPop.git'
Plugin 'davidhalter/jedi-vim.git'

"" plugin settings
let g:NERDTreeShowHidden = 1
let g:ctrlp_show_hidden = 1
let g:acp_behaviorKeywordLength = 2
let g:acp_completeoptPreview = 1
let g:acp_behaviorPythonOmniLength = -1
let g:jedi#force_py_version = 3
let g:jedi#goto_assignments_command = "<localleader>a"
let g:jedi#goto_command = "<localleader>g"
let g:jedi#goto_definitions_command = "<localleader>d"
let g:jedi#goto_stubs_command = "<localleader>s"
let g:jedi#documentation_command = "D"
let g:jedi#usages_command = "<localleader>u"
let g:jedi#rename_command = "<localleader>r"

" Key maps
"" copy / paste maps
vmap <C-c> "+yi
vmap <C-x> "+c
vmap <C-v> c<esc>"+p
imap <C-v> <C-r><C-o>+

"" custom maps
nmap <f12> :q!<cr>
nmap <C-x> <C-^><cr>
nmap <C-n> :NERDTreeToggle<cr>

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
