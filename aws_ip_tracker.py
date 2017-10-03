import argparse
import datetime
import json
import os

from netaddr import *
from pymongo import MongoClient
from tqdm import tqdm

"""
MIT License

Copyright 2017 Chapin Bryce

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

__author__ = "Chapin Bryce"
__date__ = 20171002
__description__ = "Utility to read AWS IP Address mappings into MongoDB"


class IPNotFound(Warning):
    """Warning for when an IP address queried is not found"""
    pass


class ParseIPs(object):
    def __init__(self, **kwargs):
        self.tqdm = kwargs.get('tqdm', False)
        self.host = kwargs.get('host', 'localhost')
        self.port = kwargs.get('port', 27017)
        self.mongo = MongoClient(self.host, self.port)
        self.db = self.mongo.IPTracker
        self.posts = self.db.aws_ip_ranges

    def parse(self, json_file):
        # Include DB support here

        records = self.parse_ips._parse_json_file(json_file)
        if self.tqdm:
            looper = tqdm(records)
        else:
            looper = records
        for rec in looper:
            matching_posts = self.posts.find({'first_ip': rec['first_ip'],
                                         'last_ip': rec['last_ip'],
                                         'cidr': rec['cidr']})

            if matching_posts.count() == 1:
                # Update prior record
                matching_rec = matching_posts.next()
                events = rec.get("events", []) + matching_rec.get("events", [])
                self.posts.update_one({'first_ip': rec['first_ip'],
                                 'last_ip': rec['last_ip'],
                                 'cidr': rec['cidr']},
                                {"$set": {"events": events}})
            elif matching_posts.count() > 1:
                # Throw error, should not have more than 1...
                raise Exception("Too many posts matching {} found".format(
                    str(rec)
                ))
            else:
                # Insert new record
                self.posts.insert_one(rec)
        print("All items loaded")

    def _parse_json_file(self, json_file):
        """Parse json file into individual records for the database

        Args:
            json_file: Open file-like object to turn into json data

        """
        json_data = json.load(json_file)
        collected_date = datetime.datetime.strptime(
            os.path.basename(json_file.name).split("_")[1].replace(
                ".json", ""), "%Y%m%d%H%M%S"
        )
        record_created = datetime.datetime.strptime(
            json_data.get("createDate"), "%Y-%m-%d-%H-%M-%S"
        )

        if self.tqdm:
            looper = tqdm(json_data.get("prefixes", []))
        else:
            looper = json_data.get("prefixes", [])

        records = []
        for prefix in looper:
            event = {
                "record_created": record_created,
                "record_collected": collected_date,
                "region": prefix.get("region", ""),
                "service": prefix.get("service", "")
            }
            ip_net = IPNetwork(prefix.get("ip_prefix", ""))
            records.append({
                "first_ip": ip_net.first,
                "last_ip": ip_net.last,
                "cidr": prefix.get("ip_prefix", ""),
                "events": [
                    event
                ]
            })

        return records


class QueryIP(object):
    """
    To Query IP:
        convert ip into <ip_int> with int(netaddr.IPAddress())
        {'first_ip': { $lte: <ip_int> } , 'last_ip': { $gte: <ip_int> } }
    """
    def __init__(self, **kwargs):
        self.host = kwargs.get('host', 'localhost')
        self.port = kwargs.get('port', 27017)
        self.mongo = MongoClient(self.host, self.port)
        self.db = self.mongo.IPTracker
        self.posts = self.db.aws_ip_ranges

    def query(self, ip_addr):
        """Query for records related to a single IP address

        Args:
            ip_addr (str): String IP Address. Must be in format %d.%d.%d.%d

        Returns:
            events (list): List of dictionaries containg values resulting from
                           querying the database
        """

        ip_as_int = int(IPAddress(ip_addr))
        matching_posts = self.posts.find({'first_ip': { '$lte': ip_as_int },
                                          'last_ip': { '$gte': ip_as_int }})
        events = []
        if matching_posts.count() > 0:
            # TODO consider reducing number of events using "record_created"
            for post_data in matching_posts:
                post_events = post_data.get("events", [])
                for evt in post_events:
                    events.append({
                        "cidr": post_data.get("cidr", "N/A"),
                        "service": evt.get("service", "N/A"),
                        "region": evt.get("region", "N/A"),
                        "record_created": evt.get(
                            "record_created", "N/A").isoformat(),
                        "record_collected": evt.get(
                            "record_collected", "N/A").isoformat()
                    })

        else:
            IPNotFound("IP Address {} not found in dataset".format(ip_addr))
        return events


if __name__ == '__main__':
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
    query_cmd = subparsers.add_parser("query", help="Query IP address from db")
    query_cmd.add_argument("IP_ADDR", help="IP address to query for")
    # General options
    parser.add_argument("--mongo-host", help="Host of MongoDB instance",
                        default='localhost')
    parser.add_argument("--mongo-port", help="Host of MongoDB instance",
                        default=27017, type=int)
    args = parser.parse_args()

    if args.subparser == 'ingest':
        parse_ips = ParseIPs(tqdm=True, host=args.mongo_host,
                             port=args.mongo_port)
        parse_ips.parse(args.JSON_FILE)
    elif args.subparser == 'query':
        quip = QueryIP(host=args.mongo_host, port=args.mongo_port)
        rset = quip.query(args.IP_ADDR)
        from pprint import pprint
        for entry in rset:
            pprint(entry)
