#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""NuvlaBox Peripheral GPU Manager

This service provides GPU discovery of a NuvlaBox.

It provides:
    - Nvidia Docker Runtime discovery
    - provides the correct devices and libraries needed to use a GPU.
    - checks if Docker is the correct version to use --gpus.
"""

import os
import csv
import sys
import json
from shutil import which
import subprocess
import requests
import docker
import logging
from threading import Event
import time

def init_logger():
    """ Initializes logging """

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s - %(funcName)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)


def wait_bootstrap():
    """ Simply waits for the NuvlaBox to finish bootstrapping, by pinging the Agent API
    :returns
    """

    logging.info("Checking if NuvlaBox has been initialized...")

    healthcheck_endpoint = "http://agent/api/healthcheck"

    r = requests.get(healthcheck_endpoint)
    while not r.ok:
        time.sleep(5)
        r = requests.get(healthcheck_endpoint)

    logging.info('NuvlaBox has been initialized.')
    return

def publish(url, assets):
    """
    API publishing function.
    """
    x = requests.post(url, json = assets)
    return x.json()

def readJson(jsonPath):
    """
    JSON reader.
    """
    with open(jsonPath, 'r') as f:
        dic = json.load(f)
        return dic

def readCSV(path):
    """
    CSV reader.
    """
    lines = []
    with open(path, 'r') as csvFile:
        reader = csv.reader(csvFile)
        for i in reader:
            lines.append(i)
        return lines

def filterCSV(lines):
    """
    Filters the correct information from the runtime CSV files.
    """
    filteredLines = {'devices': [], 'libraries': []}
    for i in lines:
        if i[0] == 'lib' :
            filteredLines['libraries'].append(i[1].strip())
        elif i[0] == 'dev':
            filteredLines['devices'].append(i[1].strip())

    return filteredLines


def checkCuda():
    """
    Checks if CUDA is installed and returns the version.
    """
    version = which('nvcc')
    if version is not None:
        with open(version + '/version.txt', 'r') as f:
            v = f.readline()
            return v
    else:
        return False

def dockerVersion():
    """
    Checks if the Docker Engine version and the Docker API version are enough to run --gpus.
    """
    version = docker.from_env().version()
    for i in version['Components']:
        if i['Name'] == 'Engine':
            engineVersion = int(i['Version'].split('.')[0])
            apiVersion = float(i['Details']['ApiVersion'])
            if engineVersion >= 19 and apiVersion >= 1.4:
                return True
    return False

def searchRuntime(runtimePath, hostFilesPath):
    """
    Checks if Nvidia Runtime exists, and reads its files.
    """


    for i in os.listdir(runtimePath):

        if 'daemon.json' in i:

            dic = readJson(runtimePath + i)

            if 'nvidia' in  dic['runtimes'].keys():

                a = readRuntimeFiles(hostFilesPath)
                return a

            else:
                return None

    return None

def readRuntimeFiles(path):
    """
    Checks if the runtime files exist, reads them, and filters the correct information.
    """
    if os.path.isdir(path) and len(os.listdir(path)) > 0:
        allLines = []
        for i in os.listdir(path):
            for i in readCSV(path + i):
                allLines.append(i)
        return filterCSV(allLines)
    return None

def flow(runtime, hostFilesPath):
    runtime = searchRuntime(runtime, hostFilesPath)
    if runtime is not None:
        # GPU is present and able to be used

        if dockerVersion():

            logging.info('--gpus is available...')
            runtimeFiles = {'available': True, 'name': 'GPU', 'classes':['gpu'], 'identifier': 'gpu','additional-assets': runtime}

        else:

            logging.info('--gpus is not available, but GPU usage is available')
            runtimeFiles = {'available': True, 'name': 'GPU', 'classes':['gpu'],'identifier': 'gpu','additional-assets': runtime}
    else:
        # GPU is not present or not able to be used.

        logging.info('No viable GPU available.')
        runtimeFiles = {'available': False, 'name': 'GPU', 'identifier': 'gpu','classes':['gpu']}

    logging.info(runtimeFiles)

    return runtimeFiles

def send(url, assets):
    if assets.keys() != None:
        logging.info("Sending GPU information to Nuvla")
        return publish(url, assets)
    else:
        logging.info("No GPU present...")
        return publish(url, assets)

def gpuCheck(api_url):
    logging.info('Checking if GPU already published')

    identifier = 'gpu'
    get_gpus = requests.get(api_url + '?identifier_pattern=' + identifier)
    
    logging.info(get_gpus.json())

    if not get_gpus.ok or not isinstance(get_gpus.json(), list) or len(get_gpus.json()) == 0:
        logging.info('No GPU published.')
        return False
    
    logging.info('GPU has already been published.')
    return True

if __name__ == "__main__":

    init_logger()

    wait_bootstrap()

    API_URL = "http://agent/api/peripheral"
    HOST_FILES = '/etc/nvidia-container-runtime/host-files-for-container.d/'
    RUNTIME_PATH = '/etc/docker/'


    e = Event()

    if not gpuCheck(API_URL):
        ok = False
        while not ok:
            ok = send(API_URL, flow(RUNTIME_PATH, HOST_FILES))
            e.wait(timeout=90)