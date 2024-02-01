#!/bin/sh
python3 ensure_partitions_created.py -c inventory_docker.yaml
python3 main.py -c inventory_docker.yaml
