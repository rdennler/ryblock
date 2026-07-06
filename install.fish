#!/usr/bin/env fish
# ryBlock installer — symlinks the CLI onto PATH, wires fish completions

set -l here (dirname (realpath (status --current-filename)))
set -l bin /usr/local/bin/ryblock

chmod +x $here/ryblock $here/blockd.py

echo '◢◤ linking '$bin
if test -w (dirname $bin)
    ln -sf $here/ryblock $bin
else
    sudo mkdir -p (dirname $bin)
    sudo ln -sf $here/ryblock $bin
end

set -l compdir ~/.config/fish/completions
echo '◢◤ installing completions to '$compdir
mkdir -p $compdir
ln -sf $here/completions/ryblock.fish $compdir/ryblock.fish

set -l confdir ~/.config/fish/conf.d
echo '◢◤ installing rb:* commands to '$confdir
mkdir -p $confdir
ln -sf $here/conf.d/ryblock.fish $confdir/ryblock.fish

echo '◢◤ done. open a new shell, then try: rb:help'
