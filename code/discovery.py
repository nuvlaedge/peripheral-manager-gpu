#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""NuvlaEdge Peripheral GPU Manager

This service provides GPU discovery for the NuvlaEdge.

It provides:
    - Nvidia Docker Runtime discovery
    - a list of the devices and libraries needed to use a GPU.
    - checks if Docker is the correct version to use --gpus.
"""

from gpu.gpu import main

if __name__ == '__main__':
    main()
