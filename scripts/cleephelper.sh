#!/bin/bash
#Enable Cleep daemon at raspi startup
#@see http://unix.stackexchange.com/a/164092
#@see http://unix.stackexchange.com/a/106674

function enable_on_sysvinit {
    echo "Enabling Cleep on sysvinit..."
    update-rc.d cleep defaults
    echo "Done"
    exit
}

function disable_on_sysvinit {
    echo "Disabling Cleep on sysvinit..."
    update-rc.d cleep remove
    echo "Done"
    exit
}

function enable_on_systemctl {
    echo "Enabling Cleep on systemctl..."
    systemctl enable cleep
    echo "Done"
    exit
}

function disable_on_systemctl {
    echo "Disabling Cleep on systemctl..."
    systemctl disable cleep
    echo "Done"
    exit
}

case $1 in
  enable)
    echo "Enabling Cleep at startup..."
    if [[ `systemctl 2> /dev/null` =~ -\.mount ]]; then systemctl enable cleep.service;
    elif [[ -f /etc/init.d/cron && ! -h /etc/init.d/cron ]]; then update-rc.d cleep defaults;
    else echo "Error: unable to find suitable startup system. Cleep will NOT start automatically"; exit; fi
    echo "Done"
    ;;

  disable)
    echo "Disabling Cleep from startup..."
    if [[ `systemctl 2> /dev/null` =~ -\.mount ]]; then systemctl disable cleep.service;
    elif [[ -f /etc/init.d/cron && ! -h /etc/init.d/cron ]]; then update-rc.d cleep remove;
    else echo "Error: unable to find suitable startup system. Cleep CANNOT be disabled"; exit; fi
    echo "Done"
    ;;
    
  start)
    if [[ `systemctl 2> /dev/null` =~ -\.mount ]]; then systemctl start cleep.service;
    elif [[ -f /etc/init.d/cron && ! -h /etc/init.d/cron ]]; then /etc/init.d/cleep start;
    else echo "Error: unable to find suitable startup system."; exit; fi
    ;;

  stop)
    if [[ `systemctl 2> /dev/null` =~ -\.mount ]]; then systemctl stop cleep.service;
    elif [[ -f /etc/init.d/cron && ! -h /etc/init.d/cron ]]; then /etc/init.d/cleep stop;
    else echo "Error: unable to find suitable startup system."; exit; fi
    ;;

  restart)
    if [[ `systemctl 2> /dev/null` =~ -\.mount ]]; then systemctl restart cleep.service;
    elif [[ -f /etc/init.d/cron && ! -h /etc/init.d/cron ]]; then /etc/init.d/cleep restart;
    else echo "Error: unable to find suitable startup system."; exit; fi
    ;;

  *)
    echo "Usage: cleephelper.sh <enable|disable|start|stop|restart>"
esac

