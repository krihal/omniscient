from debian:latest

ENV DEBIAN_FRONTEND noninteractive

RUN apt update
RUN apt install -y \
    python3-venv \
    python3-pip \
    iputils-ping \
    procps \
    netcat-openbsd \
    net-tools \
    curl \
    netcat-openbsd \
    supervisor \
    emacs-nox \
    && apt-get clean
RUN mkdir /worker

COPY ./docker-master/supervisord.conf /etc/supervisor/supervisord.conf
COPY ./docker-master/start_master.sh /usr/local/bin/start_master.sh
COPY requirements.txt /master/requirements.txt
COPY master.py /master/master.py
COPY config.json /master/config.json
COPY checks /master/checks
ENTRYPOINT supervisord -c /etc/supervisor/supervisord.conf
