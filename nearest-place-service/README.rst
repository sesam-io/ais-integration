=====================
Nearest place service
=====================

A python micro service template for transforming a JSON entity stream. This service is designed to be used with the `HTTP transform <https://docs.sesam.io/configuration.html#the-http-transform>`_ in a Sesam service instance.
The service will add the nearest (posta)l place to the entity in a ``nearest_place`` property, given the entity has properties ``lat`` and ``lon``. If the input entity
does not have ``lat``/``lon`` properties, the transform does nothing (i.e. returns the entity unchanged).

The added ``nearest_place`` property includes the postal code, distance (in km) and relative compass direction to the entity from the position of the nearest place (i.e. "N", "W", "NE", "SSE" and so on).
The service must be bootstrapped with the places to search in a json file.

Running locally in a virtual environment
----------------------------------------

::

  cd ais-integration/nearest-place-service/service
  virtualenv --python=python3 venv
  . venv/bin/activate
  pip install -r requirements.txt

  python transform-service.py places.json
   * Running on http://0.0.0.0:5001/ (Press CTRL+C to quit)
   * Restarting with stat
   * Debugger is active!
   * Debugger pin code: 260-787-156

The service listens on port 5001 on localhost.

Running in Docker
-----------------

::

  cd ais-integration/nearest-place-service
  docker build -t nearest-place-service .
  docker run --name nearest-place-service -p 5001:5001

Get the IP from docker:

::

  docker inspect -f '{{.Name}} - {{.NetworkSettings.IPAddress }}' nearest-place-service


JSON entities can now be posted to 'http://<ip-address-from-docker-or-localhost>:5001/transform'. The result is streamed back to the client.
Take note of the IP address, you will need to put it into the Sesam configuration file before you upload it to your Sesam instance.

Examples:

::

   $ curl -s -XPOST 'http://localhost:5001/transform' -H "Content-type: application/json" -d '[{ "_id": "jane", "name": "Jane Doe", "lat": 123456, "lon": 456787 }]' | jq -S .
   [
     {
       "_id": "jane",
       "lat": 123456,
       "lon": 456787,
       "name": "Jane Doe",
       "nearest_place": {
            "postal_code": "4015",
            "name": "Stavanger",
            "bearing": 340.0,
            "distance": 123.0,
            "direction": "NNW"
        }
     }
   ]

Note that the example uses `curl <https://curl.haxx.se/>`_ to send the request and `jq <https://stedolan.github.io/jq/>`_ prettify the response.

