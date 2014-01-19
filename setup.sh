#!/bin/sh

sudo apt-get install python-pip python-virtualenv 

virtualenv env
source env/bin/activate

pip install -r requirements.txt
