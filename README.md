# Katoomba

Read a ServiceCatalographer instance and create a report for each service.

Currently, this is geared towards reading BiodiversityCatalogue and reporting
to the BioVeL Wiki.

## Setup
Katoomba requires Python 3 and the Python `isodate` and `requests` packages.

On recent Debian/Ubuntu distributions:
```
$ sudo apt-get install python3 pip3
$ sudo pip3 install isodate requests
```

Copy the file `config.py.in` to `config.py` and edit the values.

## Running

Change to the directory containing this README file, and run using:
```
./katoomba
```

## License

Copyright 2014 Cardiff University

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
