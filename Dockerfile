FROM 192.168.1.125:5000/raspberrypios/buster:20220922

RUN apt-get -o Acquire::ForceIPv4=true update -qqy
RUN apt-get -o Acquire::ForceIPv4=true upgrade -qqy 2>/dev/null >/dev/null
RUN apt-get -o Acquire::ForceIPv4=true install python3 wget zip git -qqy

COPY cleep.deb .
RUN apt-get install ./cleep.deb -qy
RUN systemctl disable cleep

RUN python3 -m pip install -q cleepcli
RUN mkdir -p /tmp/cleep-dev/modules && REPO_DIR=/tmp/cleep-dev cleep-cli cigetmods && rm -rf /tmp/cleep-dev

RUN export CLEEP_ENV=ci
RUN cleep --stdout --noro --dryrun > cleep.log 2>&1 | true
RUN cat cleep.log && rm cleep.log

