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
__date__ = 20170918
__description__ = "Utility to read AWS IP Address mappings into MongoDB"


class ParseIPs(object):
    def __init__(self, **kwargs):
        self.tqdm = kwargs.get('tqdm', False)
        self.host = kwargs.get('host', 'localhost')
        self.port = kwargs.get('port', 27017)

    def parse(self, json_file):
        # Include DB support here
        mongo = MongoClient(self.host, self.port)
        db = mongo.IPTracker
        posts = db.aws_ip_ranges

        records = self.parse_ips._parse_json_file(json_file)
        if self.tqdm:
            looper = tqdm(records))
        else:
            looper = records
        for rec in looper:
            matching_posts = posts.find({'first_ip': rec['first_ip'],
                                         'last_ip': rec['last_ip'],
                                         'cidr': rec['cidr']})

            if matching_posts.count() == 1:
                # Update prior record
                matching_rec = matching_posts.next()
                events = rec.get("events", []) + matching_rec.get("events", [])
                posts.update_one({'first_ip': rec['first_ip'],
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
                posts.insert_one(rec)
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

        # Sample Record
        {
            # Lookup attributes
            "first_ip": "10.10.10.0",
            "last_ip": "10.10.10.255",
            "cidr": "10.10.10.0/16",
            "events": [
                # Recorded events
                {"record_created": "", "record_collected": "",
                 "region": "", "service": ""}
            ]
        }

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
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__description__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="Developed by {} on {} under the MIT License".format(
            __author__, __date__
        )
    )
    parser.add_argument("JSON_FILE", help='Path to JSON file to parse',
                        type=argparse.FileType('r'))
    parser.add_argument("--mongo-host", help="Host of MongoDB instance",
                        default='localhost')
    parser.add_argument("--mongo-port", help="Host of MongoDB instance",
                        default=27017, type=int)
    args = parser.parse_args()

    parse_ips = ParseIPs(tqdm=True, host=args.mongo_host, port=args.mongo_port)
