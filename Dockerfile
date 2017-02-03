############################################################
# Dockerfile to build a Dino Container
# Based on Debian
############################################################

# Set the base image to Ubuntu
FROM debian

# File Author / Maintainer
MAINTAINER Oscar Eriksson

# Update the sources list
RUN apt-get update

# Install basic applications
RUN apt-get install -y tar git curl nano wget dialog net-tools build-essential
RUN apt-get install -y libssl-dev libmysqlclient-dev libpq-dev
RUN wget https://www.python.org/ftp/python/3.5.2/Python-3.5.2.tar.xz
RUN tar -xvf Python-3.5.2.tar.xz
RUN cd Python-3.5.2/
RUN ./configure --prefix=/usr/local --enable-shared LDFLAGS="-Wl,-rpath /usr/local/lib"
RUN make
RUN make altinstall
RUN apt-get install -y virtualenv
RUN cd
RUN git clone https://github.com/thenetcircle/dino.git
RUN cd dino/
RUN virtualenv --python=python3.5 env
RUN source env/bin/activate
RUN pip install --upgrade pip setuptools
RUN pip install --upgrade -r requirements.txt

# Set the default directory where CMD will execute
WORKDIR ~/dino/

# Set the default command to execute
CMD dino-start.sh
