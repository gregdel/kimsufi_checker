#!/usr/bin/env python
# -*-coding:utf-8 -*

import os
import json
import datetime
import logging
import configparser
import requests
from pushover import init, Client

# Configuration from the script folder
try:
    config_file = os.path.dirname(__file__) + '/config.ini'
    config = configparser.ConfigParser()
    config.read(config_file)
    log_path = config["logs"]["log_file"]
except :
    print "No configuration file, please create a config.ini file"
    raise SystemExit

##############
#   Logger
##############
# General configuration
formatter = logging.Formatter('[%(asctime)s][%(levelname)s] - %(message)s')
logger = logging.getLogger('ks')
logger.setLevel(logging.DEBUG)

# Log to file
logfile = logging.FileHandler(log_path)
logfile.setLevel(logging.DEBUG)
logfile.setFormatter(formatter)
logger.addHandler(logfile)

# Log to console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(formatter)
logger.addHandler(console)
##############
# / Logger
##############

def main():
    # Web service URL
    url = 'https://ws.ovh.com/dedicated/r2/ws.dispatcher/getAvailability2'

    # Get model from config, seperated by comma, strip white spaces
    models_to_check = map(str.strip, str(config["ks"]["models"]).split(','))

    # Get raw data
    r = requests.get(url)
    raw_data = json.loads(r.text)
    raw_data = raw_data["answer"]["availability"]

    # Convert raw data to usable data
    data = {}
    for model in raw_data:
        zones = {}
        data[ model["reference"] ] = {zone["zone"]: zone["availability"] for zone in model["zones"]}

    # Check the models we need to monitor
    for model in models_to_check:
        for zone in data[model]:
            status = data[model][zone]
            if status != 'unknown' and status != 'unavailable':
                message = "%s available in %s with status %s" % (model, zone, status)
                logger.info(message)
                if shoud_alert(model):
                    notify(message)
            else :
                logger.info("%s not available in %s (status: %s)" % (model, zone, status))

# Send notification with pushover
def notify(message):
    token = config["pushover"]["api_token"]
    client_key = config["pushover"]["client_key"]
    client = Client(client_key, api_token=token)
    client.send_message(message, title="KS", priority=1)

# Check if a push notification needs to be done
def shoud_alert(model, number_of_minutes=config["ks"]["notification_delay"]):
    filename = "/tmp/%s.ks" % (model)
    notificatin_period = datetime.timedelta(minutes=int(number_of_minutes))

    if os.path.exists(filename):
        logger.info("File '%s' already exists" % (filename))
        update_date = datetime.datetime.fromtimestamp(os.path.getmtime(filename))
        current_date = datetime.datetime.now()
        last_update = current_date - update_date
        if last_update > notificatin_period:
            logger.info("Send notification. Last update %d seconds ago" % (last_update.total_seconds()))
            touch(filename)
            return True
        else:
            logger.info("No notification. Last update %d seconds ago" % (last_update.total_seconds()))
            return False
    else:
        logger.info("No file found. Let's create one and send notification")
        touch(filename)
        return True

# Touch a file as unix does
def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)

if __name__ == "__main__":
    main()
