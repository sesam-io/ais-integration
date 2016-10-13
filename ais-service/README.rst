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

Build the docker image with ``docker build`` in the main directory.

To run:

::

    docker run -it --rm ais-service ais-service --url http://http://153.44.253.27:5631 --sesam-url http://sesam-ip:sesam-port/api/receivers/your-pipe/entitites
