#!/bin/bash
#Enable raspiot daemon at raspi startup
#@see https://debian-administration.org/article/28/Making_scripts_run_at_boot_time_with_Debian
#@see http://unix.stackexchange.com/a/164092
#@see http://unix.stackexchange.com/a/106674

function disable_on_sysvinit {
    echo "Disabling raspiot on sysvinit..."
    update-rc.d raspiot remove
    echo Done
    exit
}

function disable_on_systemctl {
    echo "Disabling raspiot on systemctl..."
    systemctl disable raspiot
    echo Done
    exit
}

#disable raspiot on systemctl
[[ `systemctl 2> /dev/null` =~ -\.mount ]] && disable_on_systemctl
#disable raspiot on sysvinit
[[ -f /etc/init.d/cron && ! -h /etc/init.d/cron ]] && disable_on_sysvinit
