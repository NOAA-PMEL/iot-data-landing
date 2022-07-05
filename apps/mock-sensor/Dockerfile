FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY ./mock_sensor.py .
COPY ./sensors.py .
COPY ./sources.py .

CMD [ "python3", "mock_sensor.py" ]
