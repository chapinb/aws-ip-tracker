# AWS IP Address Tracker ![pylint Score](https://mperlet.github.io/pybadge/badges/8.72.svg)

Code to parse AWS IP information, load it into MongoDB, and run queries
against it.

This project is available as a web service at http://awsip.chapinb.com:8080

Uses data collected from https://ip-ranges.amazonaws.com/ip-ranges.json to
gather data about the assignment of IP ranges to different regions and services
over time.

***This tool is for research and development purposes***

## Installation

1. Download or clone from GitHub and change into the code directory.
2. Create a virtual environment. `virtualenv -p python3 venv3 && source venv3/bin/activate`
3. Install dependencies. `pip install -r requirements.txt`

## Usage

The `aws_ip_tracker.py` script allows you to both import data from the raw json
files and to run queries against ingested data.

```plaintext
(venv) $ python aws_ip_tracker.py --help
usage: aws_ip_tracker.py [-h] [--mongo-host MONGO_HOST]
                         [--mongo-port MONGO_PORT]
                         {ingest,query} ...

Utility to read AWS IP Address mappings into and query from MongoDB

positional arguments:
  {ingest,query}        Select command to run
    ingest              Read data from collected JSON file into the databse.
    query               Query IP address from db

optional arguments:
  -h, --help            show this help message and exit
  --mongo-host MONGO_HOST
                        Host of MongoDB instance (default: localhost)
  --mongo-port MONGO_PORT
                        Host of MongoDB instance (default: 27017)

Developed by Chapin Bryce on 20190121 under the MIT License
```

While the `aws_ip_tracker.py` script can query, a separate `query_mongo.py`
script handles the formatting of the returned query results. This
script also acts as an example as how to interact with the `QueryIP()` class in
the `aws_ip_tracker.py` script for your own code.

```plaintext
(venv) Z:\Development\aws-ip-tracker>python query_mongo.py --help
usage: query_mongo.py [-h] [--mongo-host MONGO_HOST] [--mongo-port MONGO_PORT]
                      [--output OUTPUT]
                      [--output-fmt {txt,json,json-lines,csv}]
                      IP_ADDR

Utility to query MongoDB for stored AWS information

positional arguments:
  IP_ADDR               IP address to query for

optional arguments:
  -h, --help            show this help message and exit
  --mongo-host MONGO_HOST
                        Host of MongoDB instance (default: localhost)
  --mongo-port MONGO_PORT
                        Host of MongoDB instance (default: 27017)
  --output OUTPUT       path to output file. If none, prints to stdout
                        (default: stdout)
  --output-fmt {txt,json,json-lines,csv}
                        format of output file (default: txt)

Developed by Chapin Bryce on 20190121 under the MIT License
```

## Contributing

Please feel free to post issues and pull requests to this GitHub page.
