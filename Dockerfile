############################################################
# Dockerfile to build a Dino Container
# Based on Debian
############################################################

# Set the base image to Ubuntu
FROM debian

# File Author / Maintainer
MAINTAINER Oscar Eriksson

# Get rid of sh, use bash instead...
RUN ln -snf /bin/bash /bin/sh

# Update the sources list
RUN apt-get update

# Install basic applications and dependencies
RUN apt-get install -y tar git curl nano wget dialog net-tools build-essential
RUN apt-get install -y libssl-dev libmysqlclient-dev libpq-dev virtualenv

# Install Python
RUN wget https://www.python.org/ftp/python/3.5.2/Python-3.5.2.tar.xz
RUN tar -xvf Python-3.5.2.tar.xz
WORKDIR /Python-3.5.2
RUN ./configure --prefix=/usr/local --enable-shared LDFLAGS="-Wl,-rpath /usr/local/lib"
RUN make
RUN make altinstall

RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python3.5 get-pip.py

# Time for Dino
WORKDIR /
RUN git clone https://github.com/thenetcircle/dino.git
WORKDIR /dino

# create the dino user and change to it, don't run as root
RUN groupadd -r dinogroup && useradd -r -g dinogroup dinouser
RUN chown -R dinouser /dino
RUN mkdir -p /home/dinouser/.cache/pip
RUN chown -R dinouser /home/dinouser/.cache/pip
USER dinouser

RUN virtualenv --python=python3.5 env
RUN source env/bin/activate && \
        pip install --upgrade pip setuptools && \
        pip install --upgrade -r requirements.txt && \
        pip install --no-deps .

# Set the default command to execute, use a bash script so we can send env vars to dino (port etc.)
CMD source env/bin/activate && ./dino-start.sh
