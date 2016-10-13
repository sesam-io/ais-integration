===========
AIS service
===========

A Python micro service that reads a live stream of AIS messages and posts them to
a Sesam HTTP source endpoint.

Synopsis
--------

::

    usage: ais-service [-h] [--url SERVER] [--sesam-url SESAM_HTTP_SOURCE_ENDPOINT]

    Virtuoso index checker

    optional arguments:


Running in Docker
-----------------

Build the docker image with ``docker -t ais-service build .`` in the main directory.

To run:

::

    docker run -it --rm ais-service ais-service -a 153.44.253.27 -p 5631 --sesam-url http://sesam-ip:sesam-port/api/receivers/your-pipe/entitites

Python example (Sesam assumed to be running on localhost port 9042 in advance):

::

   cd ais-integration/ais-service/service
   virtualenv --python=python3 venv
   . venv/bin/activate
   pip install -r requirements.txt

   python ais-service.py -a 153.44.253.27 -p 5631 http://localhost:9042/api/receivers/ais_data/entities
