" Configure clang settings (clang required)
let kbld = findfile('Kbuild', '.;/')
if !filereadable(kbld) "if not Linux Kernel development, use clang-complete (application mode)
	Bundle 'https://github.com/vim-scripts/clang-complete.git'

	let g:clang_complete_copen = 1
	let g:clang_user_options = '-Qunused-arguments'
	
	au BufWrite *.h,*.hpp,*.hxx,*.c,*.cpp,*.cxx cal g:ClangUpdateQuickFix()
endif

" Configure cscope settings (cscope required)
if has('cscope')
	"" cscope update function
	fu! UpdateCscope()
		let cs_out = findfile('cscope.out', '.;/')
		if filereadable(cs_out)
			let cs_dir = fnamemodify(cs_out, ':h')

			exe 'cs kill -1'
			exe 'cs add' cs_out cs_dir
		endif
	endfu

	"" cscope key maps
	nmap <C-\>s :cs find s <C-R>=expand("<cword>")<CR><CR>
	nmap <C-\>g :cs find g <C-R>=expand("<cword>")<CR><CR>
	nmap <C-\>c :cs find c <C-R>=expand("<cword>")<CR><CR>
	nmap <C-\>t :cs find t <C-R>=expand("<cword>")<CR><CR>
	nmap <C-\>e :cs find e <C-R>=expand("<cword>")<CR><CR>
	nmap <C-\>f :cs find f <C-R>=expand("<cfile>")<CR><CR>
	nmap <C-\>i :cs find i <C-R>=expand("<cfile>")<CR><CR>
	nmap <C-\>d :cs find d <C-R>=expand("<cword>")<CR><CR>
	
	"" settings
	se csto=1

	"" load / update cscope db
	au BufEnter *.h,*.hpp,*.hxx,*.c,*.cpp,*.cxx cal UpdateCscope()
endif
