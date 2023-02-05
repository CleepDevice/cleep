FROM 192.168.1.125:5000/raspberrypios/buster:20211202

RUN apt-get -o Acquire::ForceIPv4=true update
RUN apt-get -o Acquire::ForceIPv4=true -y install python3 wget zip git

COPY cleep.deb .
RUN apt -y install ./cleep.deb
RUN systemctl disable cleep

RUN cleep --stdout --noro --dryrun

RUN python3 -m pip install cleepcli
