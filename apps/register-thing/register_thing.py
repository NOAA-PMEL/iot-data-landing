import json
import logging
from pathlib import Path

import redis
from logfmter import Logfmter
from flask import Flask, request
from pydantic import BaseSettings
from cloudevents.http import from_http
from cloudevents.exceptions import InvalidStructuredJSON, MissingRequiredFields

handler = logging.StreamHandler()
handler.setFormatter(Logfmter())
logging.basicConfig(handlers=[handler])
L = logging.getLogger(__name__)
L.setLevel(logging.INFO)


class Settings(BaseSettings):
    host: str = '0.0.0.0'
    port: int = 8788
    debug: bool = False
    redis_url: str = 'redis://localhost:6379/0'
    dry_run: bool = False

    class Config:
        env_prefix = 'IOT_REGISTER_THING_'
        case_sensitive = False


app = Flask(__name__)
config = Settings()
rc = redis.from_url(config.redis_url)
rc.ping()


def register_thing(thing_id, ce):

    registered = False
    updated = False

    payload = ce.data['data']

    if "metadata" in payload and payload['metadata']:
        metadata = payload["metadata"]
    else:
        metadata = {}

    key = f'things:{thing_id}:metadata'

    if metadata:

        if not rc.exists(key):
            L.info("Registering thing", extra=dict(thing_id=thing_id))
            registered = True

        msg = f"Updating metadata"
        if config.dry_run is False:
            rc.set(key, json.dumps(metadata))
        else:
            msg = f'[DRY RUN] {msg}'

        updated = True
        L.info(msg, extra=dict(thing_id=thing_id, metadata=metadata))

    return registered, updated


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
    thing_id = f"{make}_{model}"
    registered, updated = register_thing(thing_id, ce)
    return {
        'registered': registered,
        'updated_metadata': updated
    }


if __name__ == "__main__":
   app.run(debug=config.debug, host=config.host, port=config.port)
