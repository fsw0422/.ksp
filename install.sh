#!/bin/bash

echo "Installing Dependencies"
if [[ "$OSTYPE" == "darwin"* ]]; then
	/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
	brew install --cask alt-tab
	brew install \
		coreutils \
		findutils \
		gnu-tar \
		gnu-sed \
		gawk \
		gnutls \
		gnu-indent \
		gnu-getopt \
		grep \
		git \
		wget \
		vim \
		ncurses \
		libevent \
		utf8proc
else
	sudo apt update
	sudo apt install -y \
		firefox \
		git \
		xclip \
		curl \
		wget \
		gnupg \
		vim-gtk3 \
		build-essential \
		apt-transport-https \
		software-properties-common \
		bison \
		libssl-dev \
		libncurses5-dev:amd64 \
		libevent-dev \
		zlib1g-dev \
		libbz2-dev \
		libreadline-dev \
		libsqlite3-dev \
		libncursesw5-dev \
		xz-utils \
		tk-dev \
		libxml2-dev \
		libxmlsec1-dev \
		libffi-dev \
		liblzma-dev \
		libcups2 \
		libpangocairo-1.0-0 \
		libatk-adaptor \
		libxss1 \
		libnss3 \
		libxcb-keysyms1 \
		x11-apps \
		libgbm1 \
		libfuse2
fi


echo "Installing ZSH"
if [[ "$OSTYPE" == "darwin"* ]]; then
	brew install zsh
else
	sudo apt install -y zsh
fi
chsh -s $(which zsh)


echo "Installing Oh-My-ZSH"
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k
wget https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Regular.ttf
wget https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Bold.ttf
wget https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Italic.ttf
wget https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Bold%20Italic.ttf
sudo mv MesloLGS* /usr/share/fonts


echo "Installing tmux 3.5"
rm -f tmux-3.5.tar.gz && rm -rf tmux-3.5
wget https://github.com/tmux/tmux/releases/download/3.5/tmux-3.5.tar.gz -O tmux-3.5.tar.gz
tar zxvf tmux-3.5.tar.gz
cd tmux-3.5
if [[ "$OSTYPE" == "darwin"* ]]; then
	./configure --enable-utf8proc
else
	./configure
fi
make -j && sudo make install
tmux kill-server
cd ..
rm -f tmux-3.5.tar.gz && rm -rf tmux-3.5


echo "Setting up Locale to 'en_US.UTF-8'"
if [[ "$OSTYPE" == "darwin"* ]]; then
	echo "MacOS does not need Locale configuration"
else
	sudo dpkg-reconfigure locales
fi


echo "Installing SDKMAN"
curl -s "https://get.sdkman.io" | bash
echo "Please install and set a global JDK version. If you have, press any key to continue..."
read response


echo "Installing Pyenv"
curl https://pyenv.run | zsh
echo "Please install and set a global Python version. If you have, press any key to continue..."
read response


echo "Installing NVM"
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
echo "Please install and set a global Node version. If you have, press any key to continue..."
read response


echo "Installing Docker"
if [[ "$OSTYPE" == "darwin"* ]]; then
	echo "Please Install Docker Desktop. If you have, press any key to continue..."
	read response
else
	curl -fsSL https://get.docker.com -o get-docker.sh
	sudo ./get-docker.sh
	sudo usermod -aG docker $USER
fi


echo "Installing Kubernetes Tools"
if [[ "$OSTYPE" == "darwin"* ]]; then
	brew install kubectl helm k9s
else
	# kubectl
	curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.32/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
	sudo chmod 644 /etc/apt/keyrings/kubernetes-apt-keyring.gpg
	echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.32/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
	sudo chmod 644 /etc/apt/sources.list.d/kubernetes.list
	sudo apt-get update
	sudo apt-get install -y kubectl
	wget https://github.com/derailed/k9s/releases/latest/download/k9s_linux_amd64.deb && apt install ./k9s_linux_amd64.deb && rm k9s_linux_amd64.deb

	# helm
	curl https://baltocdn.com/helm/signing.asc | gpg --dearmor | sudo tee /usr/share/keyrings/helm.gpg > /dev/null
	sudo apt-get install apt-transport-https --yes
	echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/helm.gpg] https://baltocdn.com/helm/stable/debian/ all main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list
	sudo apt-get update
	sudo apt-get install helm
	
	# k9s
	wget https://github.com/derailed/k9s/releases/latest/download/k9s_linux_amd64.deb
	sudo apt install ./k9s_linux_amd64.deb
	sudo rm k9s_linux_amd64.deb
fi


echo "Installing Github Copilot CLI"
if [[ "$OSTYPE" == "darwin"* ]]; then
	brew install gh
else
	(type -p wget >/dev/null || (sudo apt update && sudo apt-get install wget -y)) \
		&& sudo mkdir -p -m 755 /etc/apt/keyrings \
		&& out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg \
		&& cat $out | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
		&& sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
		&& echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
		&& sudo apt update \
		&& sudo apt install gh -y
fi
gh extension install github/gh-copilot


echo "Installing Lazygit"
if [[ "$OSTYPE" == "darwin"* ]]; then
	brew install lazygit
else
	LAZYGIT_VERSION=$(curl -s "https://api.github.com/repos/jesseduffield/lazygit/releases/latest" | grep -Po '"tag_name": "v\K[^"]*')
	curl -Lo lazygit.tar.gz "https://github.com/jesseduffield/lazygit/releases/latest/download/lazygit_${LAZYGIT_VERSION}_Linux_x86_64.tar.gz"
	tar xf lazygit.tar.gz lazygit
	sudo install lazygit /usr/local/bin
	rm -rf lazygit*
fi


echo "Generating SSH key for Github clone access"
ssh-keygen -t rsa -b 4096 -C "fsw0422@gmail.com" -f ~/.ssh/github
echo "Have you regiestered the generated key to Github? If you have, press any key to continue..."
read response


echo "Installing configs..."
git clone https://github.com/fsw0422/.ksp.git
rm -f ~/.tmux.conf && ln -s ~/.ksp/.tmux.conf ~/
rm -f ~/.p10k.zsh && ln -s ~/.ksp/.p10k.zsh ~/
rm -f ~/.zshrc && ln -s ~/.ksp/.zshrc ~/
if [ -d "/run/WSL" ]; then
	WIN_HOME=$(wslpath "$(powershell.exe -Command '$env:USERPROFILE')" | tr -d '\r')
	rm -f "$WIN_HOME/.ideavimrc" && cp ~/.ksp/.ideavimrc $WIN_HOME
else
	rm -f ~/.ideavimrc && ln -s ~/.ksp/.ideavimrc ~/
fi
rm -f ~/.vimrc && ln -s ~/.ksp/.vimrc ~/
rm -f ~/.ssh/config && ln -s ~/.ksp/ssh_config ~/.ssh/config
rm -f ~/.sdkman/etc/config && ln -s ~/.ksp/sdkman_config ~/.sdkman/etc/config


echo "********** Installation Complete **********"
echo "Please proceed to OneDrive README file and finish platform-specific settings"
echo "Press any key to start a new Tmux session"
read response
tmux