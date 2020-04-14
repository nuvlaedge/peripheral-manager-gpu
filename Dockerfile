FROM ubuntu

RUN apt update && apt install python3 python3-pip -y
RUN pip3 install -r requirements.txt
COPY discovery.py .

CMD ["python3", "discovery.py"]