FROM python:3-alpine

COPY requirements.txt .

RUN pip3 install -r ./requirements.txt
COPY discovery.py .

CMD ["python3", "discovery.py"]