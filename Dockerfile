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
RUN a=d git clone https://github.com/thenetcircle/dino.git
WORKDIR /dino
RUN virtualenv --python=python3.5 env
RUN source env/bin/activate
RUN pip install --upgrade pip setuptools
RUN pip install --upgrade -r requirements.txt
RUN pip install --no-deps .

# Set the default command to execute, use a bash script so we can send env vars to dino (port etc.)
CMD ./dino-start.sh
