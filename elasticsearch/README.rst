Starting the Elasticsearch component

::

  docker pull elasticsearch
  docker run --name elasticsearch -p 9200:9200 -p 9300:9300 -d elasticsearch

Get the IP address of the launched container:

::

  docker inspect -f '{{.Name}} - {{.NetworkSettings.IPAddress }}' elasticsearch

Upload the index definition:

::

  curl -XPUT http://<elasticsearch-ipaddress-here>:9200/ships @ships.json

Note that the IP adress you found also need to be put into the Sesam configuration
before you upload it.

