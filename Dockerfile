FROM 192.168.1.125:5000/raspberrypios/buster:20211202

RUN apt-get -o Acquire::ForceIPv4=true update
RUN apt-get -o Acquire::ForceIPv4=true upgrade -y
RUN apt-get -o Acquire::ForceIPv4=true install python3 wget zip git -y

COPY cleep.deb .
RUN apt -y install ./cleep.deb
RUN systemctl disable cleep

# always return success because Cleep could encounter errors
# starting when up-to-date core apps are not deployed yet because
# they need new release docker image
RUN cleep --stdout --noro --dryrun > cleep.log 2>&1 | true
RUN cat cleep.log && rm cleep.log

RUN python3 -m pip install cleepcli
