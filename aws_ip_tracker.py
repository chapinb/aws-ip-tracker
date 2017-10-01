import argparse
import datetime
import json
import os
from pdb import set_trace as st

from netaddr import *
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
        self.tqdm = False
        if "tqdm" in kwargs:
            self.tqdm = True


    def parse_json_file(self, json_file):
        """Parse json file into individual records for the database

        Args:
            json_file: Open file-like object to turn into json data

        """
        json_data = json.load(json_file)
        collected_date = datetime.datetime.strptime(
            os.path.basename(json_file.name).split(
                "_")[1].replace(".json", ""),
            "%Y%m%d%H%M%S"
        )
        record_created = datetime.datetime.strptime(
            json_data.get("createDate"), "%Y-%m-%d-%H-%M-%S"
        )

        if self.tqdm:
            looper = tqdm(json_data.get("prefixes", []))
        else:
            looper = json_data.get("prefixes", [])
        for prefix in looper:
            records = []
            prefix["record_created"] = record_created
            prefix["record_collected"] = collected_date
            ip_net = IPNetwork(prefix.get("ip_prefix", ""))
            for net in ip_net:
                rec = prefix.copy()
                rec['ip_addr'] = str(net)
                records.append(rec)

            yield records

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

    args = parser.parse_args()

    # Include DB support here
    from pymongo import MongoClient
    mongo = MongoClient('localhost', 27017)
    db = mongo.IPTracker
    posts = db.aws_ips

    chunk_size = 5000
    pIP = ParseIPs(tqdm=True)
    for rset in pIP.parse_json_file(args.JSON_FILE):
        for x in tqdm(range(0, len(rset), chunk_size), leave=False):
            recs = posts.insert_many(rset[x:x+chunk_size], ordered=False)
            if len(recs.inserted_ids) != len(rset[x:x+chunk_size]):
                print("{} records of {} results loaded into the db".format(
                    len(recs.inserted_ids), len(rset[x:x+chunk_size])))
    print("All items loaded")
