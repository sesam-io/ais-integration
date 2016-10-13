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

Before you can start pushing data into Sesam, you will need to set ut a HTTP endpoint pipe connected to a dataset:

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
in a ``virtualenn`` environment (python3 required) - see the README file for details.

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

Extracting lists of ships
=========================

We would like to have a list of which ships we've seen in our search index. To do this, we have

Adding "human" poisitonal information to AIS positional entities
================================================================

Having successfully made AIS data available in Sesam, our next goal is



