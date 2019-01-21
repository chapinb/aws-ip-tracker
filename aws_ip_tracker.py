"Utility to read AWS IP Address mappings into and query from MongoDB."
import argparse
import datetime
import json
import os

from netaddr import IPNetwork, IPAddress
from pymongo import MongoClient

__author__ = "Chapin Bryce"
__date__ = 20190121
__description__ = """Utility to read AWS IP Address mappings into and query
                     from MongoDB"""
__license__ = """
MIT License

Copyright 2019 Chapin Bryce

Permission is hereby granted, free of charge, to any person obtaining a copy of
  this software and associated documentation files (the "Software"), to deal in
  the Software without restriction, including without limitation the rights to
  use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
  of the Software, and to permit persons to whom the Software is furnished to
  do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
  copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
  SOFTWARE.
"""


class IPNotFound(Warning):
    """Warning for when an IP address queried is not found"""


class DBObject():
    """MongoDB Object"""
    def __init__(self, **kwargs):
        self.host = kwargs.get('host', 'localhost')
        self.port = kwargs.get('port', 27017)
        self.mongo = MongoClient(self.host, self.port)
        self.database = self.mongo.IPTracker
        self.database = self.database.aws_ip_ranges


class ParseIPs(DBObject):
    """Parse IP information into MongoDB for ease of querying"""

    def parse(self, json_file):
        """Parser of json file containing AWS IP information

        Args:
            json_file (file-obj): Open file
        """
        # Include DB support here
        for rec in self.parse_json_file(json_file):
            matching_posts = self.database.find(
                {'first_ip': rec['first_ip'],
                 'last_ip': rec['last_ip'],
                 'cidr': rec['cidr']}
            )

            if matching_posts.count() == 1:
                # Update prior record
                new_event = rec.get("events", [])
                if len(new_event) == 1:
                    self.database.update_one(
                        {'first_ip': rec['first_ip'],
                         'last_ip': rec['last_ip'], 'cidr': rec['cidr']},
                        {"$addToSet": {"events": new_event[0]}}
                    )
                elif not new_event:
                    continue
                else:
                    self.database.update_one(
                        {'first_ip': rec['first_ip'],
                         'last_ip': rec['last_ip'],
                         'cidr': rec['cidr']},
                        {"$addToSet": {"events": {"$each": new_event}}})
            elif matching_posts.count() > 1:
                # Throw error, should not have more than 1...
                raise Exception("Too many posts matching {} found".format(
                    str(rec)))
            else:
                # Insert new record
                self.database.insert_one(rec)
        print("All items loaded")

    @staticmethod
    def parse_json_file(json_file):
        """Parse json file into individual records for the database

        Args:
            json_file (file-obj): File containing valid json data

        """
        json_data = json.load(json_file)
        collected_date = datetime.datetime.strptime(
            os.path.basename(json_file.name).split("_")[1].replace(
                ".json", ""), "%Y%m%d%H%M%S"
        )
        record_created = datetime.datetime.strptime(
            json_data.get("createDate"), "%Y-%m-%d-%H-%M-%S"
        )

        for prefix in json_data.get("prefixes", []):
            event = {
                "record_created": record_created,
                "record_collected": collected_date,
                "region": prefix.get("region", ""),
                "service": prefix.get("service", "")
            }
            ip_net = IPNetwork(prefix.get("ip_prefix", ""))
            yield {
                "first_ip": ip_net.first,
                "last_ip": ip_net.last,
                "cidr": prefix.get("ip_prefix", ""),
                "events": [
                    event
                ]
            }


class QueryIP(DBObject):
    """
    To Query IP:
        convert ip into <ip_int> with int(netaddr.IPAddress())
        {'first_ip': { $lte: <ip_int> } , 'last_ip': { $gte: <ip_int> } }
    """

    def run_search(self, ip_addr):
        """Run search against the MongoDB

        Args:
            ip_addr (str): Validated IP address string to search against
                           the db

        Returns:
            List of results from MongoDB

        """
        ip_as_int = int(IPAddress(ip_addr))
        return self.database.find({'first_ip': {'$lte': ip_as_int},
                                   'last_ip': {'$gte': ip_as_int}})

    def query(self, ip_addr, format_dates=False):
        """Query for records related to a single IP address

        Args:
            ip_addr (str): String IP Address. Must be in format %d.%d.%d.%d

        Returns:
            events (list): List of dictionaries containg values resulting from
                           querying the database
        """

        matching_posts = self.run_search(ip_addr)
        all_events = []
        if matching_posts.count() > 0:
            for post_data in matching_posts:
                events = {}
                for evt in post_data.get("events", []):
                    evt_id = "{}___{}___{}".format(
                        post_data.get("cidr", "N/A"),
                        evt.get("service", "N/A"),
                        evt.get("region", "N/A"),
                    )
                    # Keep it simple - grab min/max of collected
                    if evt_id not in events:
                        events[evt_id] = {'min': evt["record_collected"],
                                          'max': evt["record_collected"]}

                    if events[evt_id]['min'] > evt["record_collected"]:
                        events[evt_id]['min'] = evt["record_collected"]

                    if events[evt_id]['max'] < evt["record_collected"]:
                        events[evt_id]['max'] = evt["record_collected"]

                # Make this mess pretty...
                for evt_id, evt_val in events.items():
                    # Format Dates
                    fcollected = evt_val['min'].isoformat()
                    lcollected = evt_val['max'].isoformat()
                    if format_dates:
                        fcollected = fcollected.replace('T', ' ')
                        lcollected = lcollected.replace('T', ' ')

                    all_events.append(
                        {
                            'cidr': evt_id.split("___")[0],
                            'service': evt_id.split("___")[1],
                            'region': evt_id.split("___")[2],
                            'first_collected': fcollected,
                            'last_collected': lcollected
                        }
                    )

        else:
            IPNotFound("IP Address {} not found in dataset".format(ip_addr))
        return all_events


if __name__ == '__main__':
    # pylint: disable=C0103
    parser = argparse.ArgumentParser(
        description=__description__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="Developed by {} on {} under the MIT License".format(
            __author__, __date__
        )
    )
    subparsers = parser.add_subparsers(help="Select command to run",
                                       dest="subparser")
    # Ingest options
    ingest_cmd = subparsers.add_parser("ingest", help="Read data from "
                                       "collected JSON file into the databse.")
    ingest_cmd.add_argument("JSON_FILE", help='Path to JSON file to parse',
                            type=argparse.FileType('r'))
    # Query options
    query_cmd = subparsers.add_parser(
        "query", help="Query IP address from db")
    query_cmd.add_argument("IP_ADDR", help="IP address to query for")
    # General options
    parser.add_argument("--mongo-host", help="Host of MongoDB instance",
                        default='localhost')
    parser.add_argument("--mongo-port", help="Host of MongoDB instance",
                        default=27017, type=int)
    args = parser.parse_args()

    if args.subparser == 'ingest':
        parse_ips = ParseIPs(host=args.mongo_host, port=args.mongo_port)
        parse_ips.parse(args.JSON_FILE)
    elif args.subparser == 'query':
        quip = QueryIP(host=args.mongo_host, port=args.mongo_port)
        rset = quip.query(args.IP_ADDR)
        from pprint import pprint
        for entry in rset:
            pprint(entry)
