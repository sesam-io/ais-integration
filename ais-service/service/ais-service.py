import ais.stream
import ais.compatibility.gpsd
from datetime import datetime, timedelta
import json
import argparse
import socket
import requests


def post_message(session, url, msg):
    json_data = json.dumps(msg)
#    print(json_data)

    r = session.post(url, params={}, headers={"content-type": "application/json"},
                     data=json_data, verify=False, timeout=3600)

    r.raise_for_status()
    r.close()


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="ais-service")
    parser.add_argument("-a", "--ais-server", dest='ais_server', help='AIS service/IP address')
    parser.add_argument("-p", "--ais-port", dest='ais_port', help='AIS service/IP port')
    parser.add_argument("-s", "--sesam-url", dest='sesam_url', help='Sesam HTTP endpoint')

    options = parser.parse_args()

    # Open socket to AIS service
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((options.ais_server, int(options.ais_port)))

    f = s.makefile()
    part_cache = {}
    i = 0

    try:
        with requests.session() as session:
            # This loop will not end as long as the socket is open

            for msg in ais.stream.decode(f):
                i += 1
                message = ais.compatibility.gpsd.mangle(msg)

                if "type" not in message or "mmsi" not in message:
                    continue

                print("Processing message #%s, type %s" % (i, message.get("type")))

                # # Check for (potential) multi-part message
                if "part_num" in message:
                    message["_id"] = "%s_%s_%s" % (message["type"], message["mmsi"], message["part_num"])
                else:
                    message["_id"] = "%s_%s" % (message["type"], message["mmsi"])

                post_message(session, options.sesam_url, message)
    finally:
        s.close()

if __name__ == '__main__':
    main()
