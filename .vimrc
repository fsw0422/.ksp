" Plugins
se rtp+=~/.ksp/
cal vundle#rc()
"" setup plugins (ctags required)
Bundle 'https://github.com/altercation/vim-colors-solarized.git'
Bundle 'https://github.com/scrooloose/nerdtree.git'
Bundle 'https://github.com/kien/ctrlp.vim.git'
Bundle 'https://github.com/vim-scripts/AutoComplPop.git'
Bundle 'https://github.com/ervandew/supertab.git'
Bundle 'https://github.com/majutsushi/tagbar.git'
Bundle 'https://github.com/tpope/vim-fugitive.git'
Bundle 'https://github.com/wkentaro/conque.vim.git'
Bundle 'https://github.com/andviro/flake8-vim.git'
Bundle 'https://github.com/davidhalter/jedi-vim.git'

"" plugin settings
let NERDTreeShowHidden = 1
let g:ctrlp_show_hidden = 1
let g:acp_behaviorKeywordLength = 2
let g:acp_completeoptPreview = 1
let g:acp_behaviorPythonOmniLength = -1
let g:SuperTabDefaultCompletionType = '<c-x><c-o>'
let g:SuperTabCrMapping = 1

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
nmap <LocalLeader>a :PyFlakeAuto<cr>
nmap <LocalLeader>1 :Gstatus<cr>
nmap <LocalLeader>2 :Gdiff<cr>
nmap <LocalLeader>3 :Gblame<cr>
nmap <LocalLeader>4 :Gpush<cr>
nmap <LocalLeader>5 :Gbrowse<cr>

if has('unix')
	nmap <LocalLeader>c :ConqueTermSplit bash<cr><cr>
	nmap <LocalLeader>vc :ConqueTermVSplit bash<cr><cr>
elseif has('win32')
	nmap <LocalLeader>c :ConqueTermSplit cmd.exe<cr><cr>
	nmap <LocalLeader>vc :ConqueTermVSplit cmd.exe<cr><cr>
endif

" Global settings
"" general
filet plugin indent on
syn on
hi Pmenusel ctermfg=White ctermbg=Blue cterm=Bold

se enc=utf-8
se tags=./tags,tags; " load ctags db
se nocp
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

if has('gui_running')
	au GuiEnter * se vb t_vb= | colo solarized

	if has("gui_gtk2")
		set gfn=Monospace\ 11
	elseif has("gui_win32")
		set gfn=Consolas:h11
	endif
endif

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

" Load add-ons
so ~/.ksp/add-on/c&c++.vim
