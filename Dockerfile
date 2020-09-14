FROM python:3-alpine

RUN apk add --no-cache docker

RUN rm -rf /var/cache/apk/*

COPY code/ /opt/nuvlabox/

WORKDIR /opt/nuvlabox/

RUN pip3 install -r requirements.txt

ENTRYPOINT ["./discovery.py"]
