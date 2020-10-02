FROM python:3-alpine

COPY code/ LICENSE /opt/nuvlabox/

WORKDIR /opt/nuvlabox/

RUN pip3 install -r ./requirements.txt

RUN rm -rf /var/cache/apk/*

ONBUILD RUN ./license.sh

ENTRYPOINT ["./discovery.py"]
