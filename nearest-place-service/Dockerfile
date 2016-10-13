FROM ubuntu:16.04

MAINTAINER Tom Bech "tom.bech@sesam.io"

EXPOSE 5001/tcp

ENV DEBIAN_FRONTEND noninteractive
RUN localedef -i en_US -f UTF-8 en_US.UTF-8
ENV LANGUAGE en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8
RUN locale-gen en_US.UTF-8
RUN dpkg-reconfigure locales
ENV PYTHON_EGG_CACHE /tmp
ENV PYTHONIOENCODING UTF-8

RUN \
apt-get update && \
apt-get install -y \
  apt-utils \
  curl \
  python3 \
  python3-dev \
  build-essential

RUN curl -sSL https://bootstrap.pypa.io/get-pip.py | python3
COPY ./service /service
WORKDIR /service
RUN pip install -r requirements.txt
ENTRYPOINT ["python3"]
CMD ["transform-service.py", "/service/places.json"]
