FROM python:3-alpine


COPY code/ /opt/nuvlabox/

WORKDIR /opt/nuvlabox/

RUN apk add docker
RUN pip3 install -r ./requirements.txt

RUN rm -rf /var/cache/apk/*

ENTRYPOINT ["./discovery.py"]
