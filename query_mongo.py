"""Utility to query MongoDB for stored AWS information"""
import argparse
import csv
import json
import sys

from aws_ip_tracker import QueryIP


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
__date__ = 20171204
__description__ = "Utility to query MongoDB for stored AWS information"


def main(mongo_host, mongo_port, ip_addr, output, output_fmt):
    """Primary controller for query script.

    Args:
        mongo_host (str): IP address of mongo host
        mongo_port (int): Port number for mongo host
        ip_addr (str): String in the format of %d.%d.%d.%d
        output (str): Path to write output to
        output_fmt (str): Format to write output as

    """
    quip = QueryIP(host=mongo_host, port=mongo_port)
    rset = quip.query(ip_addr, verbose=False)  # List of dicts

    if output == 'stdout':
        open_file = sys.stdout
    else:
        open_file = open(output, 'w', encoding='utf-8')

    if output_fmt == 'txt':
        write_txt(open_file, rset)
    elif output_fmt == 'json':
        write_json(open_file, rset)
    elif output_fmt == 'json-lines':
        write_json(open_file, rset, lines=True)
    elif output_fmt == 'csv':
        write_csv(open_file, rset)


def write_csv(open_file, rset):
    """Controller to write results as csv"""
    csv_writer = csv.DictWriter(open_file,
                                fieldnames=['cidr', 'record_created',
                                            'record_last_collected', 'region',
                                            'service'])
    csv_writer.writeheader()
    csv_writer.writerows(rset)


def write_json(open_file, rset, lines=False):
    """Controller to write results as json"""
    if lines:
        for entry in rset:
            open_file.write(json.dumps(entry)+'\n')
    else:
        open_file.write(json.dumps(rset))


def write_txt(open_file, rset):
    """Controller to write results as txt"""
    fmt = "{cidr:18} | {record_created:22} | {record_last_collected:22} | " \
          "{region:10} | {service}\n"
    open_file.write(fmt.format(cidr='cidr', record_created='record_created',
                               record_last_collected='record_last_collected',
                               region='region', service='service'))
    open_file.write("-"*91+'\n')
    for entry in rset:
        open_file.write(fmt.format(**entry))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__description__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="Developed by {} on {} under the MIT License".format(
            __author__, __date__
        )
    )
    # Query options
    parser.add_argument("IP_ADDR", help="IP address to query for")
    # General options
    parser.add_argument("--mongo-host", help="Host of MongoDB instance",
                        default='localhost')
    parser.add_argument("--mongo-port", help="Host of MongoDB instance",
                        default=27017, type=int)
    parser.add_argument("--output", help="path to output file. If none, "
                                         "prints to stdout",
                        default='stdout')
    parser.add_argument("--output-fmt", help="format of output file",
                        choices=['txt', 'json', 'json-lines', 'csv'],
                        default='txt')
    args = parser.parse_args()
    main(args.mongo_host, args.mongo_port, args.IP_ADDR, args.output,
         args.output_fmt)
