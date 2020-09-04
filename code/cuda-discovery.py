import os
from shutil import which
import subprocess

#
# Its assumed that the host has CUDA, and CUDA is available at /usr/local/, as it is the normal CUDA instalation place.
# 
#


# TODO
#   [ ] - Receive a env var and change CUDA instalation directory
#   [ ] - 

def nvidiaContainerCliCheck():
    exists = which('nvidia-container-cli')
    cuda_version, model = '', ''
    if exists:
        output = subprocess.run(['nvidia-container-cli', 'info'],stdout=subprocess.PIPE).stdout.decode('utf-8').split('\n')[:-1] # the last line is empty
        for i in output:
            if i != '':
                result = i.split(':')
                if result[0] == 'CUDA version':
                    cuda_version = result[1].strip()
                elif result[0] == 'Model':
                    model = result[1].strip()

    return cuda_version, model
                 
def getNvidiaContainerCliRequires():
    """
    This function returns the driver components needed by Nvidia-Container-CLI
    """
    exists = which('nvidia-container-cli')
    components = {'dev': [], 'lib': []}
    if exists:
        output = subprocess.run(['nvidia-container-cli', 'list'],stdout=subprocess.PIPE).stdout.decode('utf-8').split('\n')[:-1] # the last line is empty
        for i in output:
            if i.startswith('/dev/'):
                components['dev'].append(i)
            else:
                components['lib'].append(i)
    return components


def isCudaInstalled(components_list):
    for i in components_list['lib']:
        if 'cuda' in i:
            print(i)


print(isCudaInstalled(getNvidiaContainerCliRequires()))