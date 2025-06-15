#!/bin/sh
docker build -t project .
docker rm -f project_container || true
docker run -p 8000:8000 --name project_container project
