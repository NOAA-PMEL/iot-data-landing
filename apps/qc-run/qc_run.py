import dataclasses
import io
import json
import logging
from pathlib import Path
from datetime import datetime
import os 

import httpx
import boto3
import pandas as pd
from logfmter import Logfmter
from flask import Flask, request
from pydantic import BaseSettings
from botocore.config import Config
from ioos_qc.stores import PandasStore
from ioos_qc.streams import PandasStream
from ioos_qc.config import Config as QcConfig
from cloudevents.exceptions import InvalidStructuredJSON
from cloudevents.http import to_structured, from_http, CloudEvent
from google.cloud import storage

handler = logging.StreamHandler()
handler.setFormatter(Logfmter())
logging.basicConfig(handlers=[handler])
L = logging.getLogger(__name__)
L.setLevel(logging.INFO)

# Quiet the ioos_qc logs
logging.getLogger("ioos_qc").setLevel(logging.ERROR)

ENV_PREFIX = 'IOT_QC_RUN_'

class Settings(BaseSettings):
    host: str = '0.0.0.0'
    port: int = 8789
    debug: bool = False

    user: str = ''
    password: str = ''
    bucket: str = 'iot-data-landing'
    path: str = 'stage'
    endpoint: str = 'https://s3.axds.co'
    region: str = ''
    platform: str = 'gcp'
    secret_key: str = ''

    knative_broker: str = 'http://kafka-broker-ingress.knative-eventing.svc.cluster.local/default/default'

    dry_run: bool = False

    class Config:
        env_prefix = ENV_PREFIX
        case_sensitive = False


class S3Connector():

    def __init__(self, config):
        self.client = boto3.client(
                's3',
                config=Config(region_name=config.region),
                aws_access_key_id=config.user,
                aws_secret_access_key=config.password,
                endpoint_url=config.endpoint
        )

    def upload_fileobj(self, file_obj, bucket, key):
        self.client.upload_fileobj(file_obj, bucket, key)

    def download_fileobj(self, bucket, key, fobj):
        self.client.download_fileobj(bucket, key, fobj)


class GcpConnector():
    
    def __init__(self, config):
        with open('/tmp/key.json', 'w') as keyfile:
            keyfile.write(config.secret_key)

        self.client = storage.Client.from_service_account_json('/tmp/key.json')
        os.remove('/tmp/key.json')

    def upload_fileobj(self, file_obj, bucket, key):
        bucket = self.client.get_bucket(bucket)
        blob = bucket.blob(key)
        blob.upload_from_file(file_obj)

    def download_fileobj(self, bucket, key, fobj):
        bucket = self.client.get_bucket(bucket)
        blob = bucket.blob(key)
        blob.download_to_file(fobj)


app = Flask(__name__)
config = Settings()

if config.platform == 's3':
    conn = S3Connector(config)
else:
    conn = GcpConnector(config)


def upload_results(filename, registry_id, file_obj, starting=None, date_level=1):
    
    if not config.path:
        key = f'{registry_id}/qc/data/'
    else:
        key = f'{config.path}/{registry_id}/qc/data/'

    if isinstance(starting, datetime):
        if date_level >= 1:
            key += f'{starting:%Y}/'
        if date_level >= 2:
            key += f'{starting:%Y%m}/'
        if date_level >= 3:
            key += f'{starting:%Y%m%d}/'

    key += filename
    conn.upload_fileobj(file_obj, config.bucket, key)


def publish_messages(ce, messages):
    # Change to the "qc" type of event
    attrs = {
        **ce._attributes,
        **{
            'type': 'gov.noaa.pmel.acg.data.insert.envds.v2.qc'
        }
    }
    for message in messages:
        ce_msg = dict(
            data=message,
            metadata={}
        )
        try:
            data = CloudEvent(attributes=attrs, data=ce_msg)
            # Always log the message
            L.debug(data)
        except InvalidStructuredJSON:
            L.error(f"INVALID MSG: {message}")

        # Send the messages on to Kafka if we aren't in a dry_run
        if config.dry_run is False:
            try:
                headers, body = to_structured(data)
                # if config.knative_host:
                #     headers['Host'] = config.knative_host
                # send to knative kafkabroker
                with httpx.Client() as client:
                    r = client.post(
                        config.knative_broker,
                        headers=headers,
                        data=body.decode()
                    )
                    r.raise_for_status()
            except InvalidStructuredJSON:
                L.error(f"INVALID MSG: {data}")
            except httpx.HTTPError as e:
                L.error(f"HTTP Error when posting to {e.request.url!r}: {e}")


def get_qc_config(registry_id):
    """
    Get the QC config from S3, load the default.yaml config if it doesn't exist.
    Uses the convention:
        config.s3_bucket / config.s3_path / registry_id / qc / config / latest.yaml

    Args:
        registry_id (str): The unique ID of the station/sensor
    """
    if not config.path:
        key = f'{registry_id}/qc/config/latest.yaml'
    else:
        key = f'{config.path}/{registry_id}/qc/config/latest.yaml'

    try:
        fobj = io.BytesIO()
        conn.download_fileobj(config.bucket, key, fobj)
        fobj.seek(0)
        return QcConfig(io.StringIO(fobj.getvalue().decode()))
    except BaseException as e:
        L.error(f'Could not load QC config from key: {key}, falling back to default QC config. {e}.')
        #return QcConfig(Path(__file__).with_name('configs') / 'default.yaml')
        fobj = io.BytesIO()
        conn.download_fileobj(config.bucket, 'default.yaml', fobj)
        fobj.seek(0)
        return QcConfig(io.StringIO(fobj.getvalue().decode()))

@app.route('/', methods=['POST'])
def qc():

    try:
        ce = from_http(request.headers, request.get_data())
        # to support local testing...
        if isinstance(ce.data, str):
            ce.data = json.loads(ce.data)
    except InvalidStructuredJSON:
        L.error("not a valid cloudevent")
        return "not a valid cloudevent", 400

    parts = Path(ce['source']).parts
    make = parts[2]
    model = parts[3]
    registry_id = f"{make}_{model}"

    data = ce.data["data"]

    # Method 1: Load directly
    try:
        df = pd.DataFrame(data)
    except ValueError:
        # If we have all scalars, just set index to zero
        df = pd.DataFrame(data, index=[0])
    df['time'] = pd.to_datetime(df.time)

    # Method 2: If we need to massage values/lists into the dataframe
    # frame = {}
    # # Put data into a DataFrame
    # for var, values in data.items():
    #     frame[var] = values
    # df = pd.DataFrame(frame)

    # Setup stream
    ps = PandasStream(df)

    # Run QC
    qc_config = get_qc_config(registry_id)
    results = ps.run(qc_config)

    # Setup store
    store = PandasStore(results)

    # Compute any aggregations
    store.compute_aggregate(name='rollup_qc')

    # Write only the test results to the store
    results_store = store.save(write_data=False, write_axes=False)

    # Append columns from qc results back into the data
    if df.size == results_store.size:
        final_results = pd.concat([df, results_store], axis=1)
    else:
        final_results = df.copy()
        for c in results_store.columns:
            if c not in df:
                # If the sizes don't match, we take the first value and set it
                # as the entire column. this is to set the Aggregate flag
                # throughout if there are no actual QC tests performed.
                final_results = final_results.assign(**{c:results_store[c].iloc[0]})

    kws = dict(
        orient='records',
        date_unit='s',
        date_format='iso'
    )

    # Send data to Kafka to be picked up by downstream processing
    messages = json.loads(final_results.to_json(**kws))
    publish_messages(ce, messages)

    # produce JSONL file for an S3 API
    starting = final_results.time.min()
    ending = final_results.time.max()
    fname = f'{registry_id}_S{starting:%Y%m%dT%H%M%S}Z_E{ending:%Y%m%dT%H%M%S}Z.jsonl'
    str_buf = io.StringIO()
    final_results.to_json(str_buf, **kws, lines=True)
    file_obj = io.BytesIO(str_buf.getvalue().encode('utf-8'))
    upload_results(fname, registry_id, file_obj, starting=starting)

    num = len(final_results)
    msg = f'Uploaded {num} results to {fname}'
    L.info(msg)
    return msg


if __name__ == "__main__":
    app.run(debug=config.debug, host=config.host, port=config.port)
