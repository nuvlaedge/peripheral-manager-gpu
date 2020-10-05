FROM python:3-alpine

RUN rm -rf /var/cache/apk/*

COPY code/ LICENSE /opt/nuvlabox/

WORKDIR /opt/nuvlabox/

RUN pip3 install -r requirements.txt

ONBUILD RUN ./license.sh

ENTRYPOINT ["./discovery.py"]
