#!/bin/bash
#Enable raspiot daemon at raspi startup
#@see http://unix.stackexchange.com/a/164092
#@see http://unix.stackexchange.com/a/106674

function enable_on_sysvinit {
    echo "Enabling raspiot on sysvinit..."
    update-rc.d raspiot defaults
    echo "Done"
    exit
}

function disable_on_sysvinit {
    echo "Disabling raspiot on sysvinit..."
    update-rc.d raspiot remove
    echo "Done"
    exit
}

function enable_on_systemctl {
    echo "Enabling raspiot on systemctl..."
    systemctl enable raspiot
    echo "Done"
    exit
}

function disable_on_systemctl {
    echo "Disabling raspiot on systemctl..."
    systemctl disable raspiot
    echo "Done"
    exit
}

case $1 in
  enable)
    echo "Enabling raspiot at startup..."
    if [[ `systemctl 2> /dev/null` =~ -\.mount ]]; then systemctl enable raspiot.service;
    elif [[ -f /etc/init.d/cron && ! -h /etc/init.d/cron ]]; then update-rc.d raspiot defaults;
    else echo "Error: unable to find suitable startup system. Raspiot will NOT start automatically"; exit; fi
    echo "Done"
    ;;

  disable)
    echo "Disabling raspiot from startup..."
    if [[ `systemctl 2> /dev/null` =~ -\.mount ]]; then systemctl disable raspiot.service;
    elif [[ -f /etc/init.d/cron && ! -h /etc/init.d/cron ]]; then update-rc.d raspiot remove;
    else echo "Error: unable to find suitable startup system. Raspiot CANNOT be disabled"; exit; fi
    echo "Done"
    ;;
    
  start)
    if [[ `systemctl 2> /dev/null` =~ -\.mount ]]; then systemctl start raspiot.service;
    elif [[ -f /etc/init.d/cron && ! -h /etc/init.d/cron ]]; then /etc/init.d/raspiot start;
    else echo "Error: unable to find suitable startup system."; exit; fi
    ;;

  stop)
    if [[ `systemctl 2> /dev/null` =~ -\.mount ]]; then systemctl stop raspiot.service;
    elif [[ -f /etc/init.d/cron && ! -h /etc/init.d/cron ]]; then /etc/init.d/raspiot stop;
    else echo "Error: unable to find suitable startup system."; exit; fi
    ;;

  restart)
    if [[ `systemctl 2> /dev/null` =~ -\.mount ]]; then systemctl restart raspiot.service;
    elif [[ -f /etc/init.d/cron && ! -h /etc/init.d/cron ]]; then /etc/init.d/raspiot restart;
    else echo "Error: unable to find suitable startup system."; exit; fi
    ;;

  *)
    echo "Usage: raspiot_helper.sh <enable|disable|start|stop|restart>"
esac

