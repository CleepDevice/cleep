#!/bin/bash
#Enable raspiot daemon at raspi startup
#@see http://unix.stackexchange.com/a/164092
#@see http://unix.stackexchange.com/a/106674

RED='\033[0;31m'
NC='\033[0m'

function enable_on_sysvinit {
    echo "Enabling raspiot on sysvinit..."
    update-rc.d raspiot defaults
    echo "Done"
    exit
}

function enable_on_systemctl {
    echo "Enabling raspiot on systemctl..."
    systemctl enable raspiot
    echo "Done"
    exit
}

if [[ `systemctl 2> /dev/null` =~ -\.mount ]]; then enable_on_systemctl;
elif [[ -f /etc/init.d/cron && ! -h /etc/init.d/cron ]]; then enable_on_sysvinit;
else echo -e "${RED}Error: unable to find suitable startup system. Raspiot will NOT start automatically${NC}"; fi
