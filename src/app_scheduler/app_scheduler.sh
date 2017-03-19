#!/usr/bin/env bash

# Script to manage application containers at scale

# Environment setup
cd "$(dirname "$0")"
shopt -s expand_aliases
. ./docker_env.sh

# Variable assignment
action=$1
service_name=$2
current_scale=$3
increment=$4

scale_service(){
    /usr/bin/docker-compose --tlsverify --tlscert=${DOCKER_CERT_PATH}cert.pem \
       --tlscacert=${DOCKER_CERT_PATH}ca.pem --tlskey=${DOCKER_CERT_PATH}key.pem \
       --host tcp://dockerapi-private-lab1.mesoform.com:2376 --file /tmp/docker-compose.yml --project-name dockerlx \
       scale ${service_name}=$1
    echo "$(date): Scaled ${service_name} from ${current_scale} to $1" >> /tmp/app_scheduler_output
    exit 0
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