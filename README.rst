========================================
Processing real time AIS data with Sesam
========================================

.. contents:: Table of Contents
   :depth: 2
   :local:

Introduction
============

A while ago I came over a press blurb on a Norwegian tech site from the The Norwegian Coastal Administration (norwegian: Kystverket)
about the opening up of their realtime ship information database to the general public (http://www.kystverket.no/Nyheter/2016/september/apner-ais-for-publikum/,
in norwegian). Having done consulting work with various customers on Linked Open Data (and Open Data in general) for many years, this piqued my curiosity.
Most public data is more or less static or at best updated at regular intervals, so a governmental organization deciding to open their real time monitoring
data seemed to me to be interesting. Reading the article, it turned out that this was mostly about a new web map application (javascript application) and not really
about open data per se; you still have to fill out an application form to get access to the raw data, and depending on your credentials and arguments for access
you may or may not get access to the live, raw data. Bummer.

Nevertheless, I kept reading a few more of the linked pages and in a side note on the nature of the "closed data access",
there was the intriguing mention of an IP address and a port number. I pointed my Firefox browser to this address, and to my surprise I actually received a
stream of.. something. The data looked like this:

::

  !BSVDM,1,1,,B,H3m<Od4N>F34u5K<=ojjn00H8220,0*73
  !BSVDM,1,1,,A,35UeSP5000Puj;>V<B`;02mV0000,0*0F
  !BSVDM,1,1,,A,13mM0u00001FlEdWnhUuL:OT0@NW,0*17
  !BSVDM,2,1,1,A,53mN1J400000hluB2218E<=DF0T@5:1Di=@DTr0k0p?154rdR2fLMevMeN88,0*73
  !BSVDM,2,2,1,A,88888888880,2*3C

A quick bit of googling revealed this to indeed be data in AIS (IEC 62320-1) format. There is an excellent discussion on the format in more practical terms
written by Eric S. Raymond here: http://catb.org/gpsd/AIVDM.html

"Cool!" I thought, and immediately wanted to see if I could get this into Sesam and do something useful with the data. How hard could it be?
The inital goal I set was to be able to read the AIS data into Sesam, extract ship information and their position over time. I also wanted to
be able to extract this information into a Elasticsearch index so I could do geographical queries on the data (i.e. "Which ships are within
a certain radius of this point?"). I already had another dataset of places with lat lon coordinates from another source (http://www.erikbolstad.no/geo/noreg/postnummer),
so for good measure, I also wanted to be able to do more "human" queries so I could query like "which ships are near Bergen at the moment?".

So why not give it a quick shot? First order of the day; what exactly is this AIS stuff?

AIS in a nutshell
=================

AIS stands for Automatic Identification System, and is an automatic tracking system used on marine vessels such as ships, static equipment (such as buoys) but also things like search-and-rescue planes.
Ships with AIS capable equipment can exchange electronic messages over various over-the-horizon channels (radio, VHF/U-VHF etc) that other ships and sensors can read, decode and/or rebroadcast.
Sensors can be stationary AIS base stations, other ships or even satellites. AIS messages contain information such as unique identification, position, destination, status, name, course, and speed.

Norway has a network of 50 AIS base stations along the coast of Norway and two satellites in polar orbit (AISSat-1 and AISSat-2) that also captures this traffic.

For ships AIS is a important supplement to radar as it is not limited to visible (horizontal) range. For authorities it is a vital tool for monitoring ship traffic, coordinating
search-and-rescue services, port planning and so on. See https://en.wikipedia.org/wiki/Automatic_identification_system for an extended summary.


Reading AIS data into Sesam
===========================

To be able to process AIS data in Sesam, I first needed to transform the raw form of the messages into something Sesam can understand.
Sesam's native data dialect is JSON, so I had to create a microservice that can read the AIS stream and post this in JSON form to a Sesam
endpoint. I've created a github repo at https://github.com/sesam-io/ais-integration that you can clone to get it up and running.

Sesam HTTP receiver endpoint
----------------------------

Note that I assume you have access to a Sesam instance somewhere, and that its reachable via a http://sesamservice:port url.

The "complete" Sesam configuration can be found in the subfolder ``sesam-config``. I will include snippets of this config along the way to
explain what's going on.

Before you can start pushing data into Sesam, you will need to set up a HTTP endpoint pipe connected to a dataset:

::

    {
      "_id": "ais_data",
      "type": "pipe",
      "source": {
        "type": "http_endpoint"
      }
    }


This pipe will set up a JSON receiver endpoint so we can use HTTP ``POST`` operations: http://sesamservice:port/api/receivers/ais_data/entitites

The AIS microservice
--------------------

The microservice for reading Sesam data resides in the ``ais-service`` subfolder. You can either run it via Docker or as a local python service
in a ``virtualenv`` environment (python3 required) - see the README file for details.

AIS messages are in a relatively obscure 6-bit ASCII format containing bitpacked structures of various lengths, Fortunately, we don't have to decode these ourselves.
The microservice uses the ``libais`` module that is available at https://github.com/schwehr/libais to do the nitty-gritty details of parsing AIS messages.

The microservice itself is pretty simple. First, we open up a TCP socket to the IP address to the Kystverket AIS service (153.44.253.27 at port 5631) and
create a file-like object of it:

::

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((options.ais_server, int(options.ais_port)))
    f = s.makefile()

We can then read messages off this stream in a loop:

::

   for msg in ais.stream.decode(f):
      message = ais.compatibility.gpsd.mangle(msg)

Note that this loop will not end until the socker closes. The data is a live stream, so that means basically never.

The native format of ``libais`` deviates a bit in naming from the property names documented in http://catb.org/gpsd/AIVDM.html so we use a function to convert it to a more familiar ``gpsd`` format (https://en.wikipedia.org/wiki/Gpsd).

An example ``message`` object looks like this:

::

  {
    "maneuver": 0,
    "received_stations": 29,
    "slot_timeout": 3,
    "status": 0,
    "second": 31,
    "class": "AIS",
    "scaled": True,
    "course": 0,
    "raim": True,
    "type": 1,
    "lat": 62.6781005859375,
    "spare": 0,
    "sync_state": 0,
    "device": "stdin",
    "repeat": 0,
    "lon": 6.669294834136963,
    "speed": 0,
    "accuracy": True,
    "status_text": "Under way using engine",
    "turn": NaN,
    "heading": 511,
    "mmsi": 257817500
  }

There are two properies which are available in all AIS messages; ``mmsi`` and ``type``. The ``mmsi`` property contains a globally unique vessel ID and ``type`` is the kind of AIS message the object
represents (see http://catb.org/gpsd/AIVDM.html#_ais_payload_interpretation for a full list of type codes).

For my purposes, I'm only interested in two kinds of messages; positional messages of types 1-3 and 18-19, for "class A" and "class B" equipment respectively
(see https://en.wikipedia.org/wiki/Automatic_identification_system#Detailed_description:_Class_A_units and
https://en.wikipedia.org/wiki/Automatic_identification_system#Detailed_description:_Class_B_units) -
in addition I'm going to need "static" information messages containing ship names and callsigns (types 5 and 24).

Sesam need an unique identifier in a ``_id`` property when we push JSON to a receiving endpoint. Looking at the structure of these messages, it makes sense to construct this property as a concatenation
of the ``mmsi`` and ``type`` properties, dropping any message missing either of these (which shouldn't happen in any case unless the message is already garbled):

::

   for msg in ais.stream.decode(f):
      message = ais.compatibility.gpsd.mangle(msg)

      if "type" not in message or "mmsi" not in message:
          continue

      message["_id"] = "%s_%s" % (message["type"], message["mmsi"])


This payload must be converted to JSON before it can be POST'ed to the Sesam endpoint:

::

    json_data = json.dumps(msg)

    r = session.post(url, params={}, headers={"content-type": "application/json"},
                     data=json_data, verify=False, timeout=3600)


Running the service for a few minutes will easily accumulate thousands of AIS messages in the ``ais_data`` dataset. Awesome!
Looking closer at the type ``24`` messages in the dataset, I noticed that it looked like these were getting updated very often.
Using the Sesam GUI to diff the current version with the previous version revealed that it was flip-flopping between versions
with the ``part_num`` property set to either ``0`` and containing:

::

  {
    "type": 24,
    "device": "stdin",
    "repeat": 0,
    "shipname": "AAS KYSTSERVICE",
    "mmsi": 257389600,
    "class": "AIS",
    "scaled": true,
    "part_num": 0
  }


Or a version with ``part_num`` set to ``1`` and containing:

::

  {
    "class": "AIS",
    "to_bow": 0,
    "shiptype": 52,
    "to_starboard": 0,
    "vendor_id": "SMTE2A[",
    "scaled": true,
    "shiptype_text": "Tug",
    "type": 24,
    "spare": 0,
    "device": "stdin",
    "repeat": 0,
    "to_port": 0,
    "callsign": "LK3624",
    "to_stern": 0,
    "mmsi": 257389600,
    "part_num": 1
  }

So, what's going on? Reading the section for these types of messages in more detail (http://catb.org/gpsd/AIVDM.html#_type_24_static_data_report)
explained this weirdness. These types of messages turn out to be multi-part! Or rather two-part.
So, we need to extend the ``_id`` of these types of messages to include the ``part_num``
field so we don't overwrite the first part!

::

    if "part_num" in message:
        message["_id"] = "%s_%s_%s" % (message["type"], message["mmsi"], message["part_num"])
    else:
        message["_id"] = "%s_%s" % (message["type"], message["mmsi"])

Stopping the microservice, deleting the dataset in Sesam and then restarting the AIS service again gave the correct ``_id``
separation and makes sure we have both parts of this type of messages, even if they don't come in sequence (or at all).
So, now we have AIS messages in Sesam - and in less than an hour of work, including googling+research! Yay!

After having run the service for a while, I noticed that the number of messages processed and the number
of entities stored in the ``ais_data`` dataset was diverging quite a lot, almost to a 10:1 ratio.
It turns out that a lot of the messages received are duplicates, either because they are rebroadcast by others
or being received by multiple AIS transponders. Another source of duplicates is transmitting the same position
over and over when not moving. Finally, there are a static messages (types ``5`` and ``24``) that are retransmitted
fairly often and those doesn't change because they're, well, static.

Sesam will only store a new version of an entity if there is any real change (i.e. its hash changes), so here Sesam clearly
works like a efficient de-duplication engine, thus keeping the propagated upstream changes minimal. The benefit of this
is obvious if you want to build chains of dependent pipes and transformations and/or push the data to a external receiver.

Extracting lists of ships
=========================

One of the goals for this little R&D project was to accumulate a list of all ships reporting through AIS messages,
and being able to search these using Elasticsearch. To do this, I just needed to pay attention to AIS messages of type
``5`` and ``24``. As I didn't see any type ``5`` messages, even after several hours of recording, I decided to ignore
them for now.

These types of messages contain information about ship name and callsign, plus additional metadata about
ship dimensions. The messages are static, meaning they don't change over time (unless the ship is renamed or rebuilt).

I found out earlier that these messages are two-part messages and that we have no way of knowing when (or if) these
parts arrive on the wire. Ideally, I'd like to have a single message to deal with so to do this I created two
new datasets to hold ``part A`` and ``part B`` messages respectively, and a third dataset where these are merged into a
single entity (if there indeed is more than one part!).

These pipes both source from the main ``ais_data`` dataset that
contains all the messages and contain a DTL transform that filters out the entities based on type and part number.

Here's the pipe for extracting type ``24``, first part messages:

::

  {
    "_id": "ais_static_part_A",
    "type": "pipe",
    "source": {
        "type": "dataset",
        "dataset": "ais_data"
    },
    "transform": [
    {
        "type": "dtl",
        "name": "All unique reported vessel names (type 24), part A",
        "dataset": "ais_data",
        "transforms": {
            "default": [
                ["filter", ["and",
                             ["eq", "_S.part_num", 0],
                             ["eq", "_S.type", 24]
                           ]
                ],
                ["copy", "*"],
                ["add", "_id", ["string", "_S.mmsi"]]
            ]
        }
    }]
  }

Noting that in these datasets there is only a single type of message, I could collapse the ``_id`` property back to a
single ``mmsi`` value again. This would also help when merging them later.

The pipe for ``part B`` messages is identical to the one above, except for filtering on ``part_num`` values of ``1``.
Now, to get a single merged entity for these messages I needed a pipe with a ``merge_dataset`` source
(https://docs.sesam.io/configuration.html#the-merge-datasets-source).

Using its ``all`` strategy setting, it reads one or more datasets and add entities with equal ``_id`` values as
children of the (otherwise empty) output entity. The keys of these children match the ``_id`` of the dataset they came
from, making it easy to add a DTL transform to "flatten" these into the parent entity.

In my usecase, the part A and part B messages don't share any properties (or rather, the shared properties have the
same values, such as ``mmsi``) so we can simply use the DTL ``merge`` function to create a unified entity containing
all properties from the children:

::

  {
    "_id": "ais_ships",
    "type": "pipe",
    "source": {
        "type": "merge_datasets",
        "datasets": ["ais_static_part_A", "ais_static_part_B"],
        "strategy": "all"
    },
    "transform": [
      {
        "type": "dtl",
        "name": "All unique reported vessel names (type 24, merged part A and B)",
        "transforms": {
          "default": [
            ["merge", "_S.ais_static_part_A"],
            ["merge", "_S.ais_static_part_B"],
            ["add", "url", ["concat", ["list", "https://www.marinetraffic.com/en/ais/details/ships/", ["string", "_T.mmsi"]]]],
            ["remove", "_updated"],
            ["remove", "_ts"],
            ["remove", "part_num"]
          ]
        }
      }]
  }

At the end I just remove tre ``part_num`` property as it's no longer needed.

When googling for other infomation, I stumbled upon a neat site on the web which apparently contains all known vessels
with public ``mmsi`` values, so I added a constructed URL to the site for fun (see http://www.marinetraffic.com).

It contains some extra stuff like images of the ship (or class of ship) if available, which is also pretty nice.
Surprisingly - at least to me - it seems to contain images of most of the ships around the norwegian coast as well,
even small fishing vessels.

Now my Sesam instance contained an accumulated list of ships reporting in via the norwegian AIS network in the ``ais_ships``
dataset. I've since been running the service for a few days, and the number seems to quickly grow to around 2k and slowly increase
from there. I guess there is about 2k ship in Norwegian waters at any single point in time, at least according to
this AIS stream (which probably is filtered, more on that later).

Adding the last reported location to the ships dataset
======================================================

In addition to the list of ships, I also wanted to know where each ship was last located. These types of messages
are of type ``1-3`` and ``18-19``. So, the first step was to filter out the positional messages in a separate dataset:

::

  {
    "_id": "ais_position_reports",
    "type": "pipe",
    "source": {
    "type": "dataset",
      "dataset": "ais_data"
    },
    "transform": [
      {
          "type": "dtl",
          "name": "Filter out all but position reports (type 1-3 and 18-19)",
          "dataset": "ais_data",
          "transforms": {
              "default": [
                  ["filter", ["or",
                               ["eq", "_S.type", 1],
                               ["eq", "_S.type", 2],
                               ["eq", "_S.type", 3],
                               ["eq", "_S.type", 18],
                               ["eq", "_S.type", 19]]
                  ],
                  ["copy", "*"]
              ]
          }
      }]
  }

This pipe is very simple, it basically picks all messages of the correct type and copies their properties to the
``ais_position_reports`` dataset.

Armed with this information, I decided to add a new dataset that joins my ships entities in ``ais_ships`` with
matching informaton from this new dataset, picking the newest of the location report messages for the join.
The reason I chose to do this in a separate dataset is that I wanted the entities in this dataset to be automatically
updated when a new related position report arrives, using Sesams cache-invalidation algorithm. To do this,
I used the DTL ``hops`` "join" function. It joins the current entity with a matching entity in another dataset, which is
very nice, but it also tracks this fact behind the scenes so any relevant changes in the joined dataset will trigger a
automatic retransform of the dependent entity. Which is fantastic! Here's how I did it:

::

  {
    "_id": "ais_ships_with_location",
    "type": "pipe",
    "source": {
      "type": "dataset",
      "dataset": "ais_ships"
    },
    "transform": [
    {
        "type": "dtl",
        "name": "All reported vessels and their last know locations",
        "dataset": "ais_ships",
        "transforms": {
            "default": [
                ["copy", "*"],
                ["add", "_id", ["string", "_S.mmsi"]],
                ["add", "last-seen-at", ["last", ["sorted", "_.when", ["apply-hops", "apply-last-seen", {
                    "datasets": ["ais_position_reports a"],
                    "where": [
                      ["eq", "_S.mmsi", "a.mmsi"]
                    ]
                  }]]]
                ]
            ],
            "apply-last-seen": [
               ["rename", "_id", "record_id"],
               ["copy", "status_text"],
               ["copy", "lat"],
               ["copy", "lon"]
            ]
        }
    }]
  }

This new ``ais_ships_with_location`` dataset contains all ships with a reported location in a ``last-seen-at`` child
entity. A random entity from this dataset looks like:

::

   {
     "repeat": 0,
     "spare": 0,
     "callsign": "LM5504",
     "scaled": true,
     "device": "stdin",
     "vendor_id": "SRTGJE)",
     "shipname": "BLUE LADY",
     "to_starboard": 2,
     "url": "https://www.marinetraffic.com/en/ais/details/ships/257599050",
     "shiptype": 37,
     "class": "AIS",
     "to_port": 2,
     "to_stern": 7,
     "to_bow": 7,
     "type": 24,
     "mmsi": 257599050,
     "shiptype_text": "Pleasure Craft",
     "last-seen-at": {
       "record_id": "18_257599050",
       "lat": "~f59.036705017089844",
       "lon": "~f9.714373588562012"
     }
   }

Not bad for a quick hack. I'm now actually quite close to what I would like to put into Elasticsearch!
This bit of info would enable me to do geosearches. However, I also set out to add a more "human friendly" way
to search for ship positon information, so I'm still missing that part.

Adding "human" poisitonal information to AIS positional entities
================================================================

As mentioned earlier, from a previous project I had a datasource that had lat lon coordinates for all postal places
in Norway (http://www.erikbolstad.no/geo/noreg/postnummer). I wanted to integrate the positional AIS messages with
this data so I could get a more "human" location in addition to the pure numeric lat lon coordinates in these messages.

I had seen apps earlier which gave relative distances to nearby places, which I though was a nice touch - so how do I
replicate this functionality?

There are currently no geo functionality in Sesam so to do these kinds of things effectively I would have to do this
outside Sesam. Sesam has a neat mechanism for exactly this sort of thing; the ``HTTP transform``
(https://docs.sesam.io/configuration.html#the-http-transform).

The HTTP transform will send a stream of entities by HTTP to an external service for processing and consume the result
for further processing in Sesam. Exactly what I needed! I created a ``nearest-place-service`` HTTP transform service in
python which you can find in the checked out github repository I mentioned earlier. You can run the service either locally
or in Docker, see its README file for the details.

Note that the IP address and port of the running service must be inserted into the Sesam configuration file before you
upload it to your Sesam service.

The service itself uses the python ``flask`` microservice framework (http://flask.pocoo.org/) to instantiate a HTTP
POST service running at the ``/transform`` path at a particular address and port.

It accepts POST requests containing single entities or lists of entities in JSON format and will return the same
enties in the response. If the entities contain a ``lat`` and ``lon`` property, it will locate the nearest Norwegian
city (well, postal office) and compute the bearing, compass direction and distance to this. This information is then
inserted into the entity in a ``nearest_place`` child entity before it is returned to the caller.

The service takes the list of places to use as input on the command line (in JSON form) - I've included the geotagged
postal office data mentioned in the repo.

Proximity searching
-------------------

The naive approach to finding the nearest place to a given lat lon point would be to simply compute the distance to all
places and sort it. Even with small datasets this would be very slow indeed, so I didn't even attempt this approach.
A quick google for spatial lookup/serarching gave me a better solution to the problem, a K-D tree (https://en.wikipedia.org/wiki/K-d_tree).

The K-D tree (or KD-tree) is a binary spatial division data structure that partitions all input points into sets using
n-dimensional planes (i.e. lines in my case where we only have 2d coordinates) and organise these into a tree. This
makes it very easy and efficient to query for things such as neighboring points; any point is either on one one or the
other side of a given plane (line), giving us in essence a binary search pattern.

However, while the basic algorithm is fairly straightforward to implement, there is quite a bit of corner cases and
things that made me hesitant to spend too much time on this myself. Fortunately, python comes to the rescue again!

Pythons library of premade modules for all kinds of processing is awesome, including, it turns out, constructing and
quering KD trees! In fact, there are many implementations available so after a short review of the most popular ones
I picked the basic ``kdtree`` module (https://pypi.python.org/pypi/kdtree). Its API is really simple, so to read the
places into a KD tree structure:

::

    with open(sys.argv[1]) as inputfile:
        for place in json.load(inputfile):
            node = tree.add((float(place["LAT"]), float(place["LON"])))
            node.place = place

The last line is added simply so I can do a reverse look up the places dict object from query results when transforming
entities.

To find the nearest place to a particular lat lon position, I can simply call:

::

    tree_node, dist = tree.search_nn((entity_lat, entity_lon))
    place_info = tree_node.place

Simple!

Computing bearing
-----------------

Now, to compute the other values I wanted turned out to be a little more involved. To compute the direction between
lat, lon pairs you have to simplify the earth to a sphere (so called "great circle" approximations) and use spherical
trignometry using ``Haversine`` formulae (https://en.wikipedia.org/wiki/Haversine_formula). After a bit of trial and
error I must admit I ended up on Stackoverflow to get the correct soluton:

::

  def compute_bearing(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(radians, (lon1, lat1, lon2, lat2))
    bearing = atan2(sin(lon2-lon1)*cos(lat2), cos(lat1)*sin(lat2)-sin(lat1)*cos(lat2)*cos(lon2-lon1))
    bearing = degrees(bearing)

    return (bearing + 360) % 360

It turned out I had forgotten to convert the input lat lon coordinates to radians before using the trignometric
math functions! Doh!

Humans are pretty bad at reading radians, so we convert the bearing value to degrees before
we return it. The last line is to shift the output value into the correct 0..360 degrees range.

Computing directons
-------------------

I wanted the bearing also in a more human friendly compass form, more specifically in the 16-point form (https://en.wikipedia.org/wiki/Points_of_the_compass#16-wind_compass_rose).
The ``bearing`` value 0 is North with East at 90 degrees, South at 180 and West at 270, so this is a simple partiton of the circle by degress:

::

  def compute_compass_direction(bearing):
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return directions[floor(bearing/22.5)]

Computing distance
------------------

Computing the approximate distance between two lat lon pairs turned out to be *much* more complex than I anticipated.
Annoyingly, the earth is not a perfect sphere, and over larger distances the error introduced by assuming so is big
enough to make a large difference.

Over the years many have grappled with this problem and come up with various approximations to the true distance.
In 1975, a clever polish guy called Thaddeus Vincenty came up with a set of formulae that represents one of the best
efforts yet; its accuracy is on the sub-millimeter range - surely that's good enough for me!

Again python's vast library of modules saved me from a surely error-prone effort of implementing
this myself, so using the geopy library (https://github.com/geopy/geopy) I can simply call its built-in ``vincenty``
implementation, which takes two (lat, lon) pair as input:


::

  def compute_distance(lat1, lon1, lat2, lon2):
    return geopy.distance.vincenty((lat1, lon1), (lat2, lon2)).meters

Putting it all together
-----------------------

Now I have all I need to add to the transformed entities! The next step was to set up a pipe in Sesam to
read the entities in the ``ais_position_reports`` dataset and use my new HTTP transform service to find the
nearest place for the positions and pipe the result into a new dataset. First I defined the ``system`` for my
service (in this case I'm running locally - in your case you're probably going to change the URLs in the config):

::

    {
      "_id": "nearest_place",
      "type": "system:url",
      "base_url": "http://localhost:5001"
    }

Then I added the pipe:

::

  {
    "_id": "ais_position_reports_nearest_place",
    "type": "pipe",
    "source": {
		"type": "dataset",
        "dataset": "ais_position_reports"
    },
    "transform": [
      {
          "type": "http",
          "name": "Find out the nearest place of all unique position reports",
          "system": "nearest_place",
          "url": "http://localhost:5001/transform"
      },
      {
          "type": "dtl",
          "name": "Turn nearest place into a string",
          "dataset": "ais_position_reports",
          "transforms": {
              "default": [
                  ["copy", "*"],
                  ["add", "position", ["concat", ["list", ["string", ["floor", 1, ["/", "_S.nearest_place.distance", 1000.0]]], " km ", "_S.nearest_place.direction", " of ", "_S.nearest_place.name"]]],
                  ["add", "when", ["now"]]
              ]
          }
      }
    ]
  }

Note that there is in fact *two* transforms on this pipe. The first sends the entities from the source dataset through
my HTTP transform, which adds the ``nearest_place`` child entity to them. The second one adds two new properties. The first,
``position``, is a computed string on the form "xx km <DIR> of Place". Finally I wanted to have an idea of when this
data was computed, so I added the current time in the ``when`` property.

Shockingly, pressing "start" on the ``ais_position_reports_nearest_place`` pipe in the Sesam GUI resulted in zero errors
and a new ``ais_position_reports_nearest_place`` dataset appeared, containing exacly what I wanted!

This kind of thing always leaves me deeply suspicious, but inspecting the produced entities confirmed that the result was indeed as intended:

::

  {
     "repeat": 0,
     "nearest_place": {
       "direction": "NW",
       "postal_code": "6475",
       "distance": "~f541.2135566326016",
       "lon": "~f6.6742",
       "lat": "~f62.6738",
       "name": "Midsund",
       "bearing": "~f332.36777079302885"
     },
     "spare": 0,
     "type": 1,
     "accuracy": true,
     "heading": 511,
     "scaled": true,
     "status": 0,
     "sync_state": 0,
     "second": 31,
     "status_text": "Under way using engine",
     "raim": true,
     "course": 0,
     "maneuver": 0,
     "turn": "nan",
     "received_stations": 29,
     "position": "0.5 km NW of Midsund",
     "slot_timeout": 3,
     "speed": 0,
     "lon": "~f6.669294834136963",
     "when": "~t2016-10-13T10:18:23.855049984Z",
     "lat": "~f62.6781005859375",
     "device": "stdin",
     "class": "AIS",
     "mmsi": 257817500
   }

Leaving my lingering suspicions behind, I modified the original ``ais_ships_with_location`` pipe to join with this
new dataset instead:

::

  {
    "_id": "ais_ships_with_location",
    "type": "pipe",
    "source": {
		"type": "dataset",
        "dataset": "ais_ships"
    },
    "transform": [
    {
        "type": "dtl",
        "name": "All reported vessels and their last know locations",
        "dataset": "ais_ships",
        "transforms": {
            "default": [
                ["copy", "*"],
                ["add", "_id", ["string", "_S.mmsi"]],
                ["add", "last-seen-at", ["last", ["sorted", "_.when", ["apply-hops", "apply-last-seen", {
                    "datasets": ["ais_position_reports_nearest_place a"],
                    "where": [
                      ["eq", "_S.mmsi", "a.mmsi"]
                    ]
                  }]]]
                ]
            ],
            "apply-last-seen": [
               ["rename", "_id", "record_id"],
               ["copy", "status_text"],
               ["copy", "when"],
               ["copy", "position"],
               ["copy", "lat"],
               ["copy", "lon"]
            ]
        }
    }]
  }

I also added the new computed properties ``when`` and ``position``. Resetting the pipe and restarting it now yielded:

::

   {
     "repeat": 0,
     "spare": 0,
     "callsign": "LM5504",
     "scaled": true,
     "device": "stdin",
     "vendor_id": "SRTGJE)",
     "shipname": "BLUE LADY",
     "to_starboard": 2,
     "url": "https://www.marinetraffic.com/en/ais/details/ships/257599050",
     "shiptype": 37,
     "class": "AIS",
     "to_port": 2,
     "to_stern": 7,
     "to_bow": 7,
     "type": 24,
     "mmsi": 257599050,
     "shiptype_text": "Pleasure Craft",
     "last-seen-at": {
       "record_id": "18_257599050",
       "lat": "~f59.036705017089844",
       "when": "~t2016-10-13T10:18:23.854389504Z",
       "position": "1.4 km ESE of Stathelle",
       "lon": "~f9.714373588562012"
     }
   }

Sweet. Now I had all I wanted to put into Elasticsearch. At this point I had spent most of one afternoon to get to
this point, perhaps 3 or 4 hours in total. Not too shabby!

Searching the processed AIS data with Elasticsearch
===================================================

The next morning I qauickly set up Elasticsearch by pulling its official Docker image:

::

  docker pull elasticsearch
  docker run --name elasticsearch -p 9200:9200 -p 9300:9300 -d elasticsearch

To be able to talk to it from Sesam, I also needed its IP address:

::

   docker inspect -f '{{.Name}} - {{.NetworkSettings.IPAddress }}' elasticsearch

In my case it was running locally and gave its IP address as ``172.17.0.2``. YMWV.

To index the ships in Sesam, I set up a ``Elasticsearch`` system in the Sesam configuration and added a pipe with a
``Elasticsearch`` sink using this system (see https://docs.sesam.io/configuration.html#the-elasticsearch-sink):

::

  {
    "_id": "elasticsearch_index",
    "type": "system:elasticsearch",
    "hosts": ["172.17.0.2:9200"]
  },
  {
    "_id": "to_elasticsearch",
    "type": "pipe",
    "source": {
      "type": "dataset",
      "dataset": "ais_ships_with_location"
    },
    "sink": {
      "type": "elasticsearch",
      "system": "elasticsearch_index",
      "default_index": "ships",
      "default_type": "ship"
    },
    "transform": [
    {
        "type": "dtl",
        "name": "Transform to elasticsearch document",
        "dataset": "ais_ships_with_location",
        "transforms": {
            "default": [
                ["copy", "_id"],
                ["copy", "mmsi"],
                ["add", "length", ["+", "_S.to_stern", "_S.to_bow"]],
                ["add", "width", ["+", "_S.to_port", "_S.to_starboard"]],
                ["copy", "vendor_id"],
                ["copy", "callsign"],
                ["copy", "shipname"],
                ["copy", "url"],
                ["rename", "status_text", "status"],
                ["rename", "shiptype_text", "shiptype"],
                ["merge", ["apply", "apply-last-seen", "_S.last-seen-at"]]
            ],
            "apply-last-seen": [
                ["copy", "*"],
                ["add", "location", ["dict", ["list",
                                                ["list", "lat", "_S.lat"],
                                                ["list", "lon", "_S.lon"]]
                ]],
                ["remove", "lat"],
                ["remove", "lon"]
            ]
        }
    }]
  }

Looking at the original entities in the ``ais_ships_with_location`` dataset, I decided to strip away a lot of the
properties that didn't seem relevant.

I also decided to rename some of them to more friendly names. Additionally, I computed the real ``width`` and ``length`` dimensions of the ship from the various ``to_`` parts, which I though
was less confusing. Finally, I added the ``lat`` and ``lon`` coordinates from the ``last-seen-at`` child entity as
a single ``location`` object with only ``lat`` and ``lon`` keys, which Elasticsearch can grok.

To make Elasticsearch understand the shape of the documents I was going to post to it, I created a JSON schema
for the properties generated:

::

  {
    "mappings": {
      "ship": {
        "properties": {
          "mmsi": {"type": "integer"},
          "callsign": {"type": "string"},
          "shipname": {"type": "string"},
          "length": {"type": "integer"},
          "width": {"type": "integer"},
          "position": {"type": "string"},
          "when": {"type": "date"},
          "vendor_id": {"type": "string"},
          "url": {"type": "string"},
          "location": {"type": "geo_point"}
          }
       }
     }
   }

You can find it under the ``elasticsearch`` subfolder in the repo as ``ships.json``.

I then created a ``ships`` index with this definition by using ``curl`` to post to my Elasticsearch instance:

::

  curl -XPUT http://172.17.0.2:9200/ships @ships.json

Elasticsearch claimed to have ``Acknowledged`` my attempt, so after uploading the new configuration to my Sesam instance
I was thrilled to see that the ``to_elasticsearch`` pipe soon reported to have proccessed entities.

Deciding to test this bold claim, I googled a bit on Elasticsearch and its geosearch support and came up with a test query:

::

   {
     "sort" : [
         {
             "_geo_distance" : {
                 "location" : {
                       "lat" : 59.902006,
                       "lon" : 10.718077
                 },
                 "order" : "asc",
                 "unit" : "km"
             }
         }
     ],
     "query": {
       "filtered" : {
           "query" : {
               "match_all" : {}
           },
           "filter" : {
               "geo_distance" : {
                   "distance" : "5km",
                   "location" : {
                       "lat" : 59.902006,
                       "lon" : 10.718077
                   }
               }
           }
       }
     }
   }

I got the ``lat`` and ``lon`` test coordinates by opening google maps and picking a random point in the Oslo harbour
area.

According to the tutorial I found, this query should give me all documents with a ``location`` value within
5 kilometers from the search parameter, and sort it on the distance to the same point. Saving the file as ``near_oslo.json``
I executed the query against my index using ``curl``:

::

   curl -XGET 'http://172.17.0.2:9200/ships/ship/_search?pretty=true' -d @near_oslo.json

So the pipe's claim turned out to check out! The query returned the following result (I clipped it a bit to shorten
the output):

::

  {
     "took" : 104,
     "timed_out" : false,
     "_shards" : {
       "total" : 5,
       "successful" : 5,
       "failed" : 0
     },
     "hits" : {
       "total" : 27,
       "max_score" : null,
       "hits" : [ {
         "_index" : "ships",
         "_type" : "ship",
         "_id" : "258112090",
         "_score" : null,
         "_source" : {
           "when" : "2016-10-13T09:57:11.250172672Z",
           "url" : "https://www.marinetraffic.com/en/ais/details/ships/258112090",
           "position" : "0.2 km SE of Oslo",
           "shiptype" : "Sailing",
           "location" : {
             "lat" : 59.90692138671875,
             "lon" : 10.725051879882812
           },
           "record_id" : "18_258112090",
           "length" : 14,
           "width" : 4,
           "callsign" : "LK9581",
           "mmsi" : 258112090,
           "vendor_id" : "SRTD,;=",
           "shipname" : "VELIERO"
         },
         "sort" : [ 0.6698691255702985 ]
       }, {
         "_index" : "ships",
         "_type" : "ship",
         "_id" : "257831680",
         "_score" : null,
         "_source" : {
           "when" : "2016-10-13T10:11:44.093045504Z",
           "url" : "https://www.marinetraffic.com/en/ais/details/ships/257831680",
           "position" : "0.2 km SE of Oslo",
           "shiptype" : "Sailing",
           "location" : {
             "lat" : 59.90694808959961,
             "lon" : 10.72535514831543
           },
           "record_id" : "18_257831680",
           "length" : 11,
           "width" : 4,
           "callsign" : "LJ9980",
           "mmsi" : 257831680,
           "vendor_id" : "TRUEHDG",
           "shipname" : "SOLGANG"
         },
         "sort" : [ 0.6821838680598435 ]
       }
       ..
       } ]
     }
   }

Mission success!

I also tested out a few searches with the more "human" friendly position field:

Ships near Bergen:

::

  curl -XGET 'http://172.17.0.2:9200/ships/ship/_search?q=position:bergen*%20AND%20shiptype:*&pretty=true

Fishingboats near Leknes (in Lofoten islands, northern Norway):

::

  curl -XGET 'http://172.17.0.2:9200/ships/ship/_search?q=position:leknes*%20AND%20shiptype:fishing*&pretty=true

All cargo ships seen:

::

  curl -XGET 'http://172.17.0.2:9200/ships/ship/_search?q=shiptype:cargo*&pretty=true

All ships named something with "viking":

::

  curl -XGET 'http://172.17.0.2:9200/ships/ship/_search?q=shipname:viking*&pretty=true

Final notes
===========

Playing around a bit more with the Elasticsearch index and comparing it to the map service that the original article was
actually about (http://kart.kystverket.no), I quickly started to notice that some of the ships didn't turn up in my index. In fact, none of them did.
And, on closer inspection, vice versa.

It turns out that the AIS service I'm reading from contain no ships longer than 40 meters, and the public service seem
to contain no ships *shorter* than 40 meters. Not sure why Kystverket have decided to separate the data like this, but
I can only assume the "full" AIS feed you can get if your application for access is granted contains all sizes.

Later on, when I find the time and inspiration, I plan to experiment with adding additional ship data via another HTTP
transform microservice, based on the publicly available Skipsregister search page (https://www.sjofartsdir.no/skipssok/)
made by another governmental agency The Norwegian Maritime Authority (norwegian: Sjøfartsdirektoratet). Peeking
behind the scenes on that web page reveals calls to a REST API talking JSON, using a query vocabulary that looks similar
to the properties in the AIS messages.
