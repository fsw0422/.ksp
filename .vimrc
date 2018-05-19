" Vundle setup
se nocp
filet off
se rtp+=~/.ksp/
cal vundle#begin()

"" setup plugins
Plugin 'scrooloose/nerdtree.git'
Plugin 'kien/ctrlp.vim.git'
Plugin 'ervandew/supertab.git'
Plugin 'vim-scripts/AutoComplPop.git'
Plugin 'majutsushi/tagbar.git'
Plugin 'andviro/flake8-vim.git'
Plugin 'davidhalter/jedi-vim.git'
Plugin 'aklt/plantuml-syntax'

"" plugin settings
let NERDTreeShowHidden = 1
let g:ctrlp_show_hidden = 1
let g:SuperTabCrMapping = 1
let g:acp_behaviorKeywordLength = 2
let g:acp_completeoptPreview = 1
let g:acp_behaviorPythonOmniLength = -1
let g:SuperTabDefaultCompletionType = '<c-x><c-o>'
let g:jedi#force_py_version = 3

" Key maps
"" general maps
nmap <f2> gT
nmap <f3> gt
nmap <f4> :se nu!<cr>
nmap <f5> :se hls!<cr>
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
au FileType python nmap <buffer><LocalLeader>a :PyFlakeAuto<cr>
au FileType python nmap <buffer><LocalLeader>c :exe 'silent !ctags -R --fields=+l --languages=python --python-kinds=-iv -f ./.tags ./'<cr>:redraw!<cr>
au FileType markdown nmap <buffer><LocalLeader>p :exe 'silent !sensible-browser %'<cr>:redraw!<cr>
au FileType plantuml nmap <buffer><LocalLeader>p :exe 'silent !plantuml % && eog %:r.png'<cr>:redraw!<cr>

" Global settings
"" general
call vundle#end()
filet plugin indent on
syn on
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

"" operation depending on filetype
au Filetype python se ts=4 | se sw=4 | se et | retab

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
