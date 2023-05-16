import json
import logging
from pathlib import Path
import os

import httpx
from logfmter import Logfmter
from registry import registry
from flask import Flask, request
from pydantic import BaseSettings
from cloudevents.http import from_http
from cloudevents.exceptions import InvalidStructuredJSON

handler = logging.StreamHandler()
handler.setFormatter(Logfmter())
logging.basicConfig(handlers=[handler])
L = logging.getLogger(__name__)
L.setLevel(logging.INFO)

ENV_PREFIX = os.environ.get('ENV_PREFIX') or 'IOT_ERDDAP_INSERT_'

class Settings(BaseSettings):
    host: str = os.environ.get(ENV_PREFIX + 'HOST') or '0.0.0.0'
    port: int = os.environ.get(ENV_PREFIX + 'PORT') or 8787
    debug: bool = os.environ.get(ENV_PREFIX + 'DEBUG') or False
    url: str = os.environ.get(ENV_PREFIX + 'URL') or 'https://localhost:8444/erddap/tabledap'
    author: str = os.environ.get(ENV_PREFIX + 'AUTHOR') or 'super_secret_author'
    dry_run: bool = os.environ.get(ENV_PREFIX + 'DRY_RUN') or False

    class Config:
        env_prefix = ENV_PREFIX
        case_sensitive = False


app = Flask(__name__)
config = Settings()


@app.route('/', methods=['POST'])
def insert():

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
    sn = parts[4]
    registry_id = f"{make}_{model}"

    # Send to a specific datasets based on the `type`
    # CloudEvent field.
    send_all_vars = False
    erddap_dataset = f"{make}_{model}"

    if 'type' in ce and ce['type'].endswith('.qc'):
        erddap_dataset += '_QC'
        send_all_vars = True

    url = f"{config.url}/{erddap_dataset}.insert"

    params = {
        'make': make,
        'model': model,
        'serial_number': sn
    }

    try:
        variables = registry[registry_id]["variables"].keys()
    except KeyError:
        params['options'] = list(registry.keys())
        params['registry_id'] = registry_id
        L.error("Unknown sensor", extra=params)
        return f"Unknown sensor, not in {registry.keys()}", 400

    data = ce.data["data"]

    if send_all_vars is False:
        # Base this on defined metadata variables, which don't include QC vars
        for var in variables:
            try:
                values = data[var]
                if isinstance(values, list):
                    # changed to allow httpx to encode properly...I think it was being encoded twice
                    # params[var] = f"%5B{','.join([str(x) for x in values])}%5D"
                    params[var] = f"[{','.join([str(x) for x in values])}]"
                else:
                    params[var] = data[var]
            except KeyError:
                L.debug("Empty variable", extra=params)
                params[var] = "NaN"
    else:
        # Base the data coming in the message
        params.update(data)

    # had to move this to the end of the params - erddap requires is to be the last parameter
    params["author"] = config.author
    L.info(params)

    if config.dry_run is False:
        try:
            r = httpx.post(
                url,
                params=params,
                verify=False
            )
            L.info(f"Sent POST to ERRDAP @ {r.url}", extra=params)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            L.error(str(e))
            return str(e)
    else:
        msg = L.info(f"[DRY_RUN] - Didn't send POST to ERRDAP @ {url}")
        L.info(msg, extra=params)
        return msg


if __name__ == "__main__":
   app.run(debug=config.debug, host=config.host, port=config.port)
