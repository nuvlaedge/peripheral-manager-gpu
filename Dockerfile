FROM ubuntu

RUN apt update && apt install python3 python3-pip inxi -y
RUN pip3 install requests
COPY discovery.py .

CMD ["python3", "discovery.py"]