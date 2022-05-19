FROM python:3.8-slim-buster

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY ./mqtt_bridge_acg_daq.py .

CMD [ "python3", "mqtt_bridge_acg_daq.py"]