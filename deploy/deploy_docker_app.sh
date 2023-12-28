#!/bin/bash

target_folder='../docker_app'
project_folder='..'

while getopts t:p: flag
do
    case "${flag}" in
        t) target_folder=${OPTARG};;
        p) project_folder=${OPTARG};;
    esac
done

mkdir $target_folder
cp "${project_folder}/deploy/docker-compose" $target_folder
cp -r "${project_folder}/source/config" $target_folder
mkdir "${target_folder}/data"
mkdir "${target_folder}/cert"

openssl req -newkey rsa:4096 \
            -x509 \
            -sha256 \
            -days 3650 \
            -nodes \
            -out "${target_folder}/cert/public.crt" \
            -keyout "${target_folder}/cert/private.key"
