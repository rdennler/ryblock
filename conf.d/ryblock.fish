# ryBlock — friendly `rb:*` command surface.
# Thin wrappers over the `ryblock` engine on PATH. Sourced at shell start.

function rb:add    --description 'ryBlock — seal a site (+ www mirror)'; ryblock add    $argv; end
function rb:block  --description 'ryBlock — seal a site (alias)';        ryblock add    $argv; end
function rb:remove --description 'ryBlock — unseal a site';              ryblock remove $argv; end
function rb:rm     --description 'ryBlock — unseal a site (alias)';      ryblock remove $argv; end
function rb:list   --description 'ryBlock — show sealed sectors';        ryblock list   $argv; end
function rb:ls     --description 'ryBlock — show sealed sectors (alias)';ryblock list   $argv; end
function rb:flush  --description 'ryBlock — purge DNS cache';            ryblock flush  $argv; end
function rb:serve  --description 'ryBlock — OFF LIMITS page server';     ryblock serve  $argv; end
function rb:doctor --description 'ryBlock — diagnose bypass issues';     ryblock doctor $argv; end
function rb:help   --description 'ryBlock — show help';                  ryblock help   $argv; end

# ── completions ──
# unseal completes only currently-sealed domains
complete -c rb:remove -f -a '(ryblock list --plain)'
complete -c rb:rm     -f -a '(ryblock list --plain)'
complete -c rb:serve  -f -a 'start stop status'
