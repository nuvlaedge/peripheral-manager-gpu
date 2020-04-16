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

def init_logger():
    """ Initializes logging """

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s - %(funcName)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)


def publish(url, assets):
    """
    API publishing function.

    TODO: Change url, test with Nuvla.
    """
    x = requests.post(url, data = assets)

    print(x.text)

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
            filteredLines['libraries'].append(i.strip())
        elif i[0] == 'dev':
            filteredLines['devices'].append(i.strip())

    return filteredLines

def checkNvidiaContainerRuntime():
    """
    Checks if nvidia container runtime is installed.
    """
    return True if which('nvidia-container-runtime') is not None else False

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
    if checkNvidiaContainerRuntime():
        # Able to be accessed through --gpus.
        if 'daemon.json' in os.listdir(runtimePath):
            dic = readJson(runtimePath + 'daemon.json')
            if 'nvidia' in  dic['runtimes'].keys():
                a = readRuntimeFiles(hostFilesPath)
                return {'path': dic['runtimes']['nvidia']['path'], 'files' : a}
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
    if checkNvidiaContainerRuntime():
        if dockerVersion():
            runtimeFiles = searchRuntime(runtime, hostFilesPath)
        else:
            runtimeFiles = searchRuntime(runtime, hostFilesPath)
    else:
        runtimeFiles = {}
    return {'additional-assets': runtimeFiles}

def send(url, flow):
    publish(url, flow)

if __name__ == "__main__":
    init_logger()
    
    API_URL = "http://agent/api/peripheral"
    HOST_FILES = '/etc/nvidia-container-runtime/host-files-for-container.d/'
    RUNTIME_PATH = '/etc/docker/'
    send(API_URL, flow(RUNTIME_PATH, HOST_FILES))