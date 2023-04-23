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

COPY ./docker-worker/supervisord.conf /etc/supervisor/supervisord.conf
COPY ./docker-worker/start_worker.sh /usr/local/bin/start_worker.sh
COPY requirements.txt /worker/requirements.txt
COPY worker.py /worker/worker.py
COPY scheduler.py /worker/scheduler.py
COPY log.py /worker/log.py

ENTRYPOINT supervisord -c /etc/supervisor/supervisord.conf
