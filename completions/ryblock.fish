# fish completions for ryblock
complete -c ryblock -f

complete -c ryblock -n __fish_use_subcommand -a add    -d 'Seal a site (+ www mirror)'
complete -c ryblock -n __fish_use_subcommand -a remove -d 'Unseal a site'
complete -c ryblock -n __fish_use_subcommand -a list   -d 'Show sealed sectors'
complete -c ryblock -n __fish_use_subcommand -a flush  -d 'Purge DNS cache'
complete -c ryblock -n __fish_use_subcommand -a serve  -d 'OFF LIMITS page server on :80'
complete -c ryblock -n __fish_use_subcommand -a help   -d 'Show help'

# remove completes only currently blocked domains
complete -c ryblock -n '__fish_seen_subcommand_from remove rm unblock' \
    -a '(ryblock list --plain)'

complete -c ryblock -n '__fish_seen_subcommand_from serve' -a 'start stop status'
