#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""NuvlaBox Peripheral GPU Manager

This service provides GPU discovery for the NuvlaBox.

It provides:
    - Nvidia Docker Runtime discovery
    - a list of the devices and libraries needed to use a GPU.
    - checks if Docker is the correct version to use --gpus.
"""

import os
import csv
import sys
import json
from shutil import which
import requests
import docker
import logging
from threading import Event
import time
from packaging import version


logging.basicConfig(level=logging.INFO)
identifier = 'GPU'
image = 'nuvlabox_cuda_core_information:{}'


def wait_bootstrap(healthcheck_endpoint="http://agent/api/healthcheck"):
    """ Simply waits for the NuvlaBox to finish bootstrapping, by pinging the Agent API
    :returns
    """

    logging.info("Checking if NuvlaBox has been initialized...")

    while True:
        try:
            r = requests.get(healthcheck_endpoint)
        except requests.exceptions.ConnectionError as e:
            logging.warning(f'Unable to establish connection with NuvlaBox Agent: {e}. Will keep trying...')
            time.sleep(10)
            continue

        if r.ok:
            break

    logging.info('NuvlaBox has been initialized.')
    return


def publish(url, assets):
    """
    API publishing function.
    """

    x = requests.post(url, json=assets)
    return x.json()


def readJson(jsonPath):
    """
    JSON reader.
    """

    with open(jsonPath) as f:
        dic = json.load(f)
        return dic


def getDeviceType():
    """
    Gets device type (x86_64, aarch64, arm64)
    """
    return os.uname().machine


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


def nvidiaDevice(devices):
    """
    Checks if any Nvidia device exist
    """
    nvDevices = []

    for device in devices:
        if device.startswith('nv'):
            nvDevices.append('/dev/{}'.format(device))
    
    return nvDevices


def checkCudaInstalation(version):
    """
    Checks if Cuda is installed.
    """
    if 'libcuda.so' in os.listdir('/usr/lib/{}-linux-gnu'.format(version)):
        return True
    else:
        return False


def buildCudaCoreDockerCLI(devices):
    """
    Creates the correct device and volume structures to be passed to docker.
    """
    cli_devices = []
    cli_volumes = {}
    libs = []

    current_devices = ['/dev/{}'.format(i) for i in os.listdir('/dev/')]

    for device in devices:
        
        if device in current_devices:
            cli_devices.append('{0}:{0}:rwm'.format(device))
    
    version = getDeviceType()
    
    # Due to differences in the implementation of the GPUs by Nvidia, in the Jetson devices, and
    #   in the discrete graphics, there is a need for different volumes. 

    if version == 'aarch64':
        libcuda = '/usr/lib/{0}-linux-gnu/'.format(version)
        etc = '/etc/'
        cli_volumes[etc] = {'bind':  etc, 'mode': 'ro'}
        libs.extend([libcuda, etc])
    else:
        libcuda = '/usr/lib/{0}-linux-gnu/libcuda.so'.format(version)
        libs.extend([libcuda])
    cuda = '/usr/local/cuda'

    libs.extend([cuda])
    cli_volumes[libcuda] = {'bind': libcuda, 'mode': 'ro'}
    cli_volumes[cuda] = {'bind': cuda, 'mode': 'ro'}

    return cli_devices, cli_volumes, libs


def getCurrentImageVersion(client):

    peripheralVersion = ''
    cudaCoreVersion = ''
    
    for container in client.containers.list():
        repotags = container.image.attrs.get('RepoTags')
        if not repotags:
            continue
        img, tag = repotags[0].split(':')
        if img == 'nuvlabox/peripheral-manager-gpu':
            peripheralVersion = tag
        elif img == image:
            cudaCoreVersion = tag

    if version.parse(peripheralVersion) > version.parse(cudaCoreVersion):
        return peripheralVersion

    else:
        return '0.0.1'
     


def cudaCores(image, devices, volumes, gpus):
    """
    Starts Cuda Core container and returns the output from the container
    """

    client = docker.from_env()

    currentVersion = getCurrentImageVersion(client)
    img = image.format(currentVersion)

    # Build Image
    if len(client.images.list(img)) == 0 and currentVersion != '':
        logging.info('Build CUDA Cores Image')
        client.images.build(path='.', tag=img, dockerfile='Dockerfile.gpu')

    container_name = 'get-cuda-cores'
    container = ''
    try:
        container = client.containers.run(img,
                                          name=container_name,
                                          devices=devices,
                                          volumes=volumes,
                                          remove=True)
    except docker.errors.APIError as e:
        if '409' in str(e):
            client.api.remove_container(container_name)
            container = client.containers.run(img,
                                              name=container_name,
                                              devices=devices,
                                              volumes=volumes,
                                              remove=True)
        else:
            pass
    except Exception as e:
        logging.error(f'Unable to infer CUDA cores. Reason: {str(e)}')
        pass    # let's not stop the peripheral manager just because we can't get this property

    return str(container)


def cudaInformation(output):
    """
    Gets the output from the container and returns GPU information
    """
    device_information = []
    info = [i.split(":")[1] for i in output.split('\\n')[1:-1]]
    # device_information['device-name'] = info[1]
    device_information.append({'unit': 'multiprocessors', 'capacity': info[3]})
    device_information.append({'unit': 'cuda-cores', 'capacity': info[4]})
    # device_information['gpu-clock'] = info[6]
    # device_information['memory-clock'] = info[7]
    device_information.append({'unit': info[8].split()[-1], 'capacity': info[8].split()[0]})

    return info[1], device_information


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

            try:
                if 'nvidia' in dic['runtimes'].keys():
                    a = readRuntimeFiles(hostFilesPath)

                    return a
                else:
                    return None
            except KeyError:
                logging.exception("Runtimes not configured in Docker configuration")
                return None

    return None


def readRuntimeFiles(path):
    """
    Checks if the runtime files exist, reads them, and filters the correct information.
    """
    if os.path.isdir(path) and len(os.listdir(path)) > 0:
        filteredLines = {'devices': [], 'libraries': []}

        for i in os.listdir(path):

            with open(path + i) as csvFile:
                reader = csv.reader(csvFile)

                for line in reader:
                    try:
                        if line[0] == 'lib':
                            filteredLines['libraries'].append(line[1].strip())

                        elif line[0] == 'dev':
                            filteredLines['devices'].append(line[1].strip())

                        else:
                            continue
                    except IndexError:
                        continue

        return filteredLines
    return None


def cudaCoresInformation(nvDevices, gpus):
    
    devices, libs, _ = buildCudaCoreDockerCLI(nvDevices)
    output = cudaCores(image, devices, libs, gpus)
    if output != '':
        try:
            name, information = cudaInformation(output)
            return name, information
        except:
            logging.exception('Exception in cudaCoresInformation')

    return None, None


def flow(runtime, hostFilesPath):
    runtime = searchRuntime(runtime, hostFilesPath)

    runtimeFiles = {
        'available': True,
        'name': 'Graphics Processing Unit',
        'vendor': 'Nvidia',
        'classes': ['gpu'],
        'identifier': identifier,
        'interface': 'gpu',
        'additional-assets': runtime
    }

    if runtime is not None:

        # GPU is present and able to be used

        if dockerVersion():
            logging.info('--gpus is available in Docker...')

        else:
            logging.info('--gpus is not available in Docker, but GPU usage is available')
        name, info = cudaCoresInformation(runtime['devices'], True)

        runtimeFiles['name'] = name
        runtimeFiles['resources'] = info

        logging.info(runtimeFiles)
        return runtimeFiles

    elif len(nvidiaDevice(os.listdir('/dev/'))) > 0 and checkCudaInstalation(getDeviceType()):

        # A GPU is present, and ready to be used, but not with --gpus
        nvDevices = nvidiaDevice(os.listdir('/dev/'))
        _, _, formatedLibs = buildCudaCoreDockerCLI(nvDevices)

        runtime = {'devices': nvDevices, 'libraries': formatedLibs}

        name, info = cudaCoresInformation(runtime['devices'], True)

        runtimeFiles['name'] = name
        runtimeFiles['additional-assets'] = runtime
        runtimeFiles['resources'] = info
        logging.info(runtimeFiles)
        return runtimeFiles

    else:

        # GPU is not present or not able to be used.
        logging.info('No viable GPU available.')

        return None


def send(url, assets):
    """ Sends POST request for registering new peripheral """

    logging.info("Sending GPU information to Nuvla")
    return publish(url, assets)


def gpuCheck(api_url):
    """ Checks if peripheral already exists """

    logging.info('Checking if GPU already published')

    get_gpus = requests.get(api_url + '?identifier_pattern=' + identifier)
    
    logging.info(get_gpus.json())

    if not get_gpus.ok or not isinstance(get_gpus.json(), list) or len(get_gpus.json()) == 0:
        logging.info('No GPU published.')
        return True
    
    logging.info('GPU has already been published.')
    return False


if __name__ == "__main__":

    API_BASE_URL = "http://agent/api"

    wait_bootstrap()

    API_URL = API_BASE_URL + "/peripheral"
    HOST_FILES = '/etcfs/nvidia-container-runtime/host-files-for-container.d/'
    RUNTIME_PATH = '/etcfs/docker/'

    e = Event()

    while True:

        gpu_peripheral = flow(RUNTIME_PATH, HOST_FILES)

        if gpu_peripheral:
            peripheral_already_registered = gpuCheck(API_URL)

            if peripheral_already_registered:
                send(API_URL, gpu_peripheral)

        e.wait(timeout=90)
