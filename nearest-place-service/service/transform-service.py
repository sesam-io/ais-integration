from flask import Flask, request, Response
import json
import os
import json
import sys
import collections
import kdtree
from math import *
from geopy.distance import vincenty

app = Flask(__name__)

places = []


def compute_compass_direction(bearing):
    # Standard 16 point compass directions from degrees
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return directions[floor(bearing/22.5)]


def compute_bearing(lat1, lon1, lat2, lon2):
    # Use Haversine to compute bearing
    lon1, lat1, lon2, lat2 = map(radians, (lon1, lat1, lon2, lat2))
    bearing = atan2(sin(lon2-lon1)*cos(lat2), cos(lat1)*sin(lat2)-sin(lat1)*cos(lat2)*cos(lon2-lon1))
    bearing = degrees(bearing)

    return (bearing + 360) % 360


def compute_distance(lat1, lon1, lat2, lon2):
    # Use Vicenty formulae to compute distance
    return vincenty((lat1, lon1), (lat2, lon2)).meters


def get_entity_lat_lon(entity):
    # Decode values if transit encoded
    if isinstance(entity["lat"], str):
        if entity["lat"].startswith("~f") or entity["lat"].startswith("~d"):
            entity_lat = float(entity["lat"][2:])
        else:
            raise AssertionError("Lat/lon must be floats or decimals if transit encoded")
    else:
        entity_lat = float(entity["lat"])

    if isinstance(entity["lon"], str):
        if entity["lon"].startswith("~f") or entity["lon"].startswith("~d"):
            entity_lon = float(entity["lon"][2:])
        else:
            raise AssertionError("Lat/lon must be floats or decimals if transit encoded")
    else:
        entity_lon = float(entity["lon"])

    return entity_lat, entity_lon


def transform_entity(entity):
    if "lat" in entity and "lon" in entity:
        # Extract lat/lon from entity
        entity_lat, entity_lon = get_entity_lat_lon(entity)

        # Find nearest place
        node, dist = tree.search_nn((entity_lat, entity_lon))
        place = node.place
        place_lat, place_lon = node.data

        # Compute bearing, distance and compass direction
        bearing = compute_bearing(place_lat, place_lon, entity_lat, entity_lon)
        direction = compute_compass_direction(bearing)
        distance = compute_distance(place_lat, place_lon, entity_lat, entity_lon)

        # Add data about place and relative position to entity and return it
        entity["nearest_place"] = {
            "postal_code": place["POSTNR"],
            "name": place["POSTSTAD"],
            "bearing": bearing,
            "direction": direction,
            "distance": distance,
            "lat": place_lat,
            "lon": place_lon
        }

    return entity


@app.route('/transform', methods=['POST'])
def receiver():

    def generate(entities):
        yield "["
        for index, entity in enumerate(entities):
            if index > 0:
                yield ","
            entity = transform_entity(entity)
            yield json.dumps(entity)
        yield "]"

    # get entities from request
    print(request)
    entities = request.get_json()
    print(entities)

    # create the response
    return Response(generate(entities), mimetype='application/json')


if __name__ == '__main__':
    global tree
    global places

    if len(sys.argv) != 2:
        raise AssertionError("The service takes a single argument (path to places json file)")

    Point = collections.namedtuple('Point', 'name lat lon')
    tree = kdtree.create(dimensions=2)

    # Load the places and construct a KDtree of them
    with open(sys.argv[1]) as inputfile:
        for place in json.load(inputfile):
            if place["POSTNR"].startswith('00') or place["POSTSTAD"].lower().find('ikkje i bruk') > -1:
                continue

            places.append(place)
            node = tree.add((float(place["LAT"]), float(place["LON"])))
            node.place = place

    print("Loaded %s places..." % len(places))

    app.run(debug=True, host='0.0.0.0', port=5001)

