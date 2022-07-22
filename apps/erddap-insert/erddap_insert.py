import json
import logging
from pathlib import Path

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


class Settings(BaseSettings):
    host: str = '0.0.0.0'
    port: int = 8787
    debug: bool = False
    url: str = 'https://localhost:8443/erddap/tabledap'
    author: str = 'super_secret_author'
    dry_run: bool = False

    class Config:
        env_prefix = 'IOT_ERDDAP_INSERT_'
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
    url = f"{config.url}/{registry_id}.insert"
    params = {
        'make': make,
        'model': model,
        'serial_number': sn,
        # 'author': config.author
    }

    try:
        variables = registry[registry_id]["variables"].keys()
    except KeyError:
        params['options'] = list(registry.keys())
        params['registry_id'] = registry_id
        L.error("Unknown sensor", extra=params)
        return f"Unknown sensor, not in {registry.keys()}", 400

    data = ce.data["data"]

    # need to check shape here?
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

    # had to move this to the end of the params - erddap requires is to be the last parameter
    params["author"] = config.author
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
