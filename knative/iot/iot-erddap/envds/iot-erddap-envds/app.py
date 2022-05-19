from flask import Flask, request
import requests
import json
from registry import registry
from cloudevents.http import CloudEvent, event, from_json, to_structured, from_http
from cloudevents.exceptions import InvalidStructuredJSON, MissingRequiredFields
import os

app = Flask(__name__)

def send_to_erddap(request):
    ce = from_http(request.headers, request.get_data())
    print(f"ce data: {ce}")
    # process data and send to erddap
    return ce['type'], ce['source']




@app.route('/insert', methods=['POST'])
# @app.route('/', methods=['POST'])
def handle_insert():

    urlbase = "https://wallingford.pmel.noaa.gov:8444/erddap/tabledap"

    try:
        ce = from_http(request.headers, request.get_data())
    except InvalidStructuredJSON:
        print("not a valid cloudevent")
        return "not a valid cloudevent"

    # print(f"ce: {ce.data}")
    # return f"ce: {ce.data}"
    # type = ce['type']
    source = ce['source']
    parts = source.split("/")
    make = parts[2]
    model = parts[3]
    sn = parts[4]
    registry_id = f"{make}_{model}"
    # dataset = f"{make}_{model}_{sn}"
    dataset = f"{make}_{model}"
    verb = "insert"
    urltarget = ".".join([dataset, verb])
    url = "/".join([urlbase, urltarget])
    author = "envds_secretkey"

    try:
        # print(registry_id)
        variables = registry[registry_id]["variables"].keys()
    except KeyError:
        print("unknown sensor")
        return

    params = []
    params.append(f"make={make}")
    params.append(f"model={model}")
    params.append(f"serial_number={sn}")

    data = ce.data["data"]
    print(f"insert new data: {data}")

    # print(data)
    # need to check shape here?
    for var in variables:
        try:
            # print(f"{var}: {data[var]}")
            values = data[var]
            if isinstance(values, list):
                # print(f"{var}: [{','.join([str(x) for x in values])}]")
                # params.append(f"{var}=[{','.join([str(x) for x in values])}]")
                params.append(f"{var}=%5B{','.join([str(x) for x in values])}%5D")
            else:
                params.append(f"{var}={data[var]}")
        except KeyError:
            # logger ->
            print("empty variable")
            # print(f"{var}: NaN")
            params.append(f"{var}=NaN")

    params.append(f"author={author}")
    
    urlparams = "&".join(params)

    postURL = "?".join([url,urlparams])
    print(f"postURL: {postURL}")
    postURL_encode = requests
    # postURL = "https://wallingford.pmel.noaa.gov:8444/erddap/tabledap/MockCo_Sensor-1_1234.insert?make=MockCo&model=Sensor-1&serial_number=1234&time=2022-04-20T00:26:02Z&latitude=9.931&longitude=-150.039&altitude=106.362&temperature=22.068&rh=55.722&wind_speed=10.116&wind_direction=81.328&author=envds_secretkey"
    resp = requests.post(postURL, verify=False)
    print(f"resp: {resp}")
    return f"{resp}"
    # return


@app.route('/', methods=['GET', 'POST'])
# @app.route('/', methods=['POST'])
def main():
    # return "main: does nothing"
    if request.method == 'POST':
        # t, s = send_to_erddap(request)
        # print(f"POST: {request.headers}")
        # return f"POST: {t}, {s}"
        return f"{request}"
    else:
        # print(f"GET: {request.headers}")
        return f"GET: {request.headers}"

if __name__ == "__main__":
   app.run(debug=True,host='0.0.0.0',port=int(os.environ.get('PORT', 8080)))
