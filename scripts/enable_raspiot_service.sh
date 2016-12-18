#!/bin/bash
#Enable raspiot daemon at raspi startup
#@see https://debian-administration.org/article/28/Making_scripts_run_at_boot_time_with_Debian
#@see http://unix.stackexchange.com/a/164092
#@see http://unix.stackexchange.com/a/106674

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

#enable raspiot on systemctl
[[ `systemctl 2> /dev/null` =~ -\.mount ]] && enable_on_systemctl ; exit
#enable raspiot on sysvinit
[[ -f /etc/init.d/cron && ! -h /etc/init.d/cron ]] && enable_on_sysvinit ; exit
