#!/usr/bin/env bash
export DOCKER_CERT_PATH=/root/.sdc/docker/gaz
export DOCKER_HOST=tcp://dockerapi-private-lab1.mesoform.com:2376
export DOCKER_CLIENT_TIMEOUT=300
export COMPOSE_HTTP_TIMEOUT=300
alias docker="docker --tls"
