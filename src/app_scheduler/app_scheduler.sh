#!/usr/bin/env bash

# Script to manage application containers at scale

# Environment setup
cd "$(dirname "$0")"
shopt -s expand_aliases
source docker_env.sh

# Variable assignment
action=$1
service_name=$2
current_scale=$3
increment=$4

scale_service(){
    docker-compose -f /tmp/docker-compose.yml -p dockerlx scale ${service_name}=$1
}

scale_up(){
    desired_scale=$((current_scale + increment))
    scale_service ${desired_scale}
}

scale_down(){
    desired_scale=$((current_scale - increment))
    scale_service ${desired_scale}
}

resize_up(){
    echo "resize container with more resources"
}

resize_down(){
    echo "resize container with less resources"
}

service_ps(){
    docker-compose -f /tmp/docker-compose.yml -p dockerlx ps
}

# run specified action
${action}
