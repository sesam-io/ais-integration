=====================
Nearest place service
=====================

A python micro service template for transforming a JSON entity stream. This service is designed to be used with the `HTTP transform <https://docs.sesam.io/configuration.html#the-http-transform>`_ in a Sesam service instance.
The service will add the nearest (posta)l place to the entity in a ``nearest_place`` property, given the entity has properties ``lat`` and ``lon``. If the input entity
does not have ``lat``/``lon`` properties, the transform does nothing (i.e. returns the entity unchanged).

The added ``nearest_place`` property includes the bearing (in degrees where 0 is North), postal code, distance (in meters) and relative 16-point compass
direction to the entity from the position of the nearest place (i.e. "N", "W", "NE", "SSE" and so on). The bearing and direction are relative from nearest place (i.e. "3 km NNE of some-place").
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
  docker run -it --rm --name nearest-place-service -p 5001:5001 nearest-place-service


Get the IP from docker:

::

  docker inspect -f '{{.Name}} - {{.NetworkSettings.IPAddress }}' nearest-place-service


JSON entities can now be posted to 'http://<ip-address-from-docker-or-localhost>:5001/transform'. The result is streamed back to the client.
Take note of the IP address, you will need to put it into the Sesam configuration file before you upload it to your Sesam instance.

Examples:

::

   $ curl -s -XPOST 'http://localhost:5001/transform' -H "Content-type: application/json" -d '[{ "_id": "jane", "name": "Jane Doe", "lat": 58.995903, "lon": 10.082722}]' | jq -S .
    [
      {
        "_id": "jane",
        "lat": 58.995903,
        "lon": 10.082722,
        "name": "Jane Doe",
        "nearest_place": {
          "bearing": 170.2446453605429,
          "direction": "SSE",
          "distance": 3963.305464313277,
          "lat": 59.030966,
          "lon": 10.071019,
          "name": "Larvik",
          "postal_code": "3260"
        }
      }
    ]


Note that the example uses `curl <https://curl.haxx.se/>`_ to send the request and `jq <https://stedolan.github.io/jq/>`_ prettify the response.

