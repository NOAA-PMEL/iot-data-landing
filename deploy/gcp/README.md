# GCP Deploy

## Set up gcloud

Work through these instructions to get gcloud installed:
<https://cloud.google.com/sdk/docs/install-sdk#deb>

## Integrate with `kubectl`

1. Create a google kubernetes engine if it does not already exist: https://console.cloud.google.com/kubernetes/list/overview?project=pmel-iot 

2. Associate kubectl with the GKE cluster

```shell
gcloud container clusters get-credentials CLUSTER_NAME --region=COMPUTE_REGION

# In our case, something like
gcloud container clusters get-credentials cluster-1 --region us-central1-c
```

Check for kubernetes service

```shell
kubectl get svc
NAME         TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)   AGE
kubernetes   ClusterIP   10.116.0.1   <none>        443/TCP   29s
```

# Build the Cluster

## Storage

```shell
kubectl apply -f deploy/gcp/prod/01_storage.yaml
```

## Kafka

```shell
kubectl create namespace kafka
kubectl create -n kafka -f 'https://strimzi.io/install/latest?namespace=kafka'
kubectl apply -f deploy/gcp/prod/02_kafka.yaml
```

### Verify the following services exist

```shell
kubectl get svc -n kafka

NAME                                 TYPE        CLUSTER-IP    EXTERNAL-IP   PORT(S)
cluster-1-kafka-0                    NodePort    10.8.6.128    <none>        9094:30069/TCP                        
cluster-1-kafka-bootstrap            ClusterIP   10.8.12.52    <none>        9091/TCP,9092/TCP,9093/TCP            
cluster-1-kafka-brokers              ClusterIP   None          <none>        9090/TCP,9091/TCP,9092/TCP,9093/TCP   
cluster-1-kafka-external-bootstrap   NodePort    10.8.13.144   <none>        9094:30702/TCP                        
cluster-1-zookeeper-client           ClusterIP   10.8.2.227    <none>        2181/TCP                              
cluster-1-zookeeper-nodes            ClusterIP   None          <none>        2181/TCP,2888/TCP,3888/TCP            
```

## Kourier (for Knative Serving)
Work through the following commands.

```shell
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.10.1/serving-crds.yaml
kubectl apply --filename https://github.com/knative/serving/releases/download/knative-v1.10.1/serving-core.yaml
kubectl apply -f https://github.com/knative/net-kourier/releases/download/knative-v1.10.0/kourier.yaml
kubectl patch configmap/config-network   --namespace knative-serving   --type merge   --patch '{"data":{"ingress-class":"kourier.ingress.networking.knative.dev"}}'
export PROXY_IP=$(kubectl get -o jsonpath="{.status.loadBalancer.ingress[0].ip}" service -n kourier-system kourier)
echo $PROXY_IP

34.69.221.225


kubectl patch configmap/config-domain --namespace knative-serving --type merge --patch "{\"data\":{\"$PROXY_IP.sslip.io\":\"\"}}"
kubectl apply -f deploy/gcp/prod/05_knative_example.yaml 

curl -v http://helloworld-go.default.$PROXY_IP.sslip.io

*   Trying 34.69.221.225:80...
* Connected to helloworld-go.default.34.69.221.225.sslip.io (34.69.221.225) port 80 (#0)
> GET / HTTP/1.1
> Host: helloworld-go.default.34.69.221.225.sslip.io
> User-Agent: curl/7.81.0
> Accept: */*
> 
* Mark bundle as not supporting multiuse
< HTTP/1.1 200 OK
< content-length: 25
< content-type: text/plain; charset=utf-8
< date: Wed, 10 May 2023 23:07:12 GMT
< x-envoy-upstream-service-time: 3245
< server: envoy
< 
Hello  - It is Working!!
* Connection #0 to host helloworld-go.default.34.69.221.225.sslip.io left intact
```

## Knative Eventing

```shell
kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.10.0/eventing-crds.yaml
kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.10.0/eventing-core.yaml

kubectl apply -f https://github.com/knative-sandbox/eventing-kafka-broker/releases/download/knative-v1.10.0/eventing-kafka-controller.yaml
kubectl apply -f https://github.com/knative-sandbox/eventing-kafka-broker/releases/download/knative-v1.10.0/eventing-kafka-broker.yaml

kubectl create secret --namespace knative-eventing generic iot-data-landing-kafka-secret \
  --from-literal=protocol=SASL_PLAINTEXT \
  --from-literal=sasl.mechanism=PLAIN \  
  --from-literal=user=iot-data-landing-kafka-user \  
  --from-literal=password=[password]

kubectl apply -f deploy/gcp/prod/07_knative_eventing_config.yaml 

kn broker list

NAME      URL                                                                              AGE   CONDITIONS   READY   REASON
default   http://kafka-broker-ingress.knative-eventing.svc.cluster.local/default/default   4m    7 OK / 7     True   
```

## Mosquitto

```shell
kubectl apply -f dev/mqtt/certs.yaml
kubectl apply -f dev/mqtt/mosquitto.yaml
```

## Mock Sensor
The Mock Sensor creates dummy sensor data and sends it to the Mosquitto broker as a cloud event. You can run this locally on your own machine. 

```shell
cd apps/mock-sensor
docker build -t mock_sensor:latest .

# Get the external-ip of the Mosquitto LoadBalancer
kubectl get service erddap

NAME     TYPE           CLUSTER-IP   EXTERNAL-IP      PORT(S)                         AGE
erddap   LoadBalancer   10.8.7.25    34.173.238.218   8080:32425/TCP,8443:32586/TCP   3d23h

# Now, run the mock sensor

docker run -e IOT_MOCK_SENSOR_MQTT_BROKER={external-ip} mock_sensor:latest

# you can also overwrite the default topic prefix by running 

docker run -e IOT_MOCK_SENSOR_MQTT_BROKER={external-ip} -e IOT_MOCK_SENSOR_MQTT_TOPIC_PREFIX={your-prefix} mock_sensor:latest
```

## MQTT Bridge

```shell
cd apps/mqtt-bridge

docker build -t mqtt_bridge:latest .

docker tag mqtt_bridge:latest harbor.axds.co/iot-data-landing/mqtt_bridge:latest
docker push harbor.axds.co/iot-data-landing/mqtt_bridge:latest

kubectl apply -f bridge-config.yaml

# running the command above will create the default configuration from bridge-config.yaml. to update, you
# can run commands like:

kubectl patch configmap/mqtt-bridge --type merge --patch '{"data":{"mqtt_broker":"34.31.21.190"}}'

# at the very least, you will need to patch the mqtt_broker with mosquitto's EXTERNAL-IP 
# which you can find by running `kubectl get service`
# you will also need to patch the mqtt_topic_filter to match what you used for your mock sensor

kubectl apply -f mqtt-bridge.yaml
```

## ERDDAP

```shell
# Running from project root

./deploy/gcp/prod/create_configmaps.sh
kubectl apply -f deploy/gcp/prod/03_erddap_service.yaml
kubectl apply -f deploy/gcp/prod/03_erddap_pvc.yaml
```

The above commands set up some configuration needed to deploy ERDDAP. To actually deploy:

```shell
# manually update the ip address in 03_erddap.yaml

kubectl get svc

NAME        TYPE           CLUSTER-IP    EXTERNAL-IP       PORT(S)
erddap      LoadBalancer   10.8.7.25     34.173.238.218    8080:32425/TCP,8443:32586/TCP

# replace the ENV variables ERDDAP_baseUrl and ERDDAP_baseHttpsUrl in 03_erddap.yaml
- name: ERDDAP_baseUrl
  value: http://[external-ip]:8080
- name: ERDDAP_baseHttpsUrl
  value: https://[external-ip]:8443
  
kubectl apply -f deploy/gcp/prod/03_erddap.yaml

./deploy/gcp/prod/copy_datasets.sh $(kubectl get pods --selector=app=erddap --output=jsonpath='{.items[*].metadata.name}')
```

Running the copy_dataset.sh script will copy the 4 datasets (Sensor-1, Sensor-1_QC, Sensor-2, Sensor-2_QC) XML files to /datasets/d on the erddap pod. It will also create directories like
/erddapData/storage/iot-data-landing/MockCo/{dataset-name} that each have a bootstrap.jsonl inside them. This is necessary for making the datasets visible in tabledap.

This process is definitely a flaw in erddap and makes it difficult to add new datasets. From what I can tell, every time you want to add a new dataset you’ll have to manually add the XML for it and a dummy .jsonl file with fake data, then restart erddap.

To get these datasets to actually show up, we need to restart erddap. Run the following:

```shell
kubectl delete -f deploy/gcp/prod/03_erddap.yaml
kubectl apply -f deploy/gcp/prod/03_erddap.yaml

# run the following and take note of the external-ip for the erddap service
kubectl get service

NAME            TYPE           CLUSTER-IP    EXTERNAL-IP         PORT(S)
erddap          LoadBalancer   10.8.7.25     34.173.238.218      8080:32425/TCP,8443:32586/TCP
```

Now, you should be able to visit http://{your-external-ip}:8080/erddap and see your instance of erddap. You can click on View a List of All 5 Datasets to see the tabledap view.


## ERDDAP Insert

```shell
cd apps/erddap-insert

docker build -t erddap_insert:latest .

docker tag erddap_insert:latest harbor.axds.co/iot-data-landing/erddap_insert:latest
docker push harbor.axds.co/iot-data-landing/erddap_insert:latest

# pushing this to harbor.axds.co is temperamental, so you might have to try it a few times
```

Using the EXTERNAL-IP that you got above (from kubectl get service), change the value of `IOT_ERDDAP_INSERT_URL` in `erddap-insert.yaml` to `https://{external-ip}/erddap/tabledap`

 Then, still inside the `/apps/erddap-insert` directory:

 ```shell
kubectl apply erddap-insert.yaml
 ```

 This creates the deployment that will receive cloud events and POST them to ERDDAP.


 ## QC Run

 If you are using the iot-data-landing bucket that currently exists under the iot-data-landing project on GCP (<https://console.cloud.google.com/storage/browser/iot-data-landing;tab=objects?forceOnBucketsSortingFiltering=true&project=pmel-iot&prefix=&forceOnObjectsSortingFiltering=false>), you will not need to do these next few instructions. However, if you make a new bucket, there are a few steps you’ll need to take.

1. Create your bucket.
   1. Insert your `default.yaml` file, which holds your default QC configuration
2. In the google cloud console, go to IAM & Admin -> Service Accounts
   1. Create a new service account with editor permissions
   2. Once created, click on the account, go to 'KEYS', click 'ADD KEY' -> Create New Key -> JSON
   3. This will download a JSON key to your computer. You need to run `kubectl create secret generic gcp-secret-key --from-file=path/to/the/key/file.json
   4. Once you do this, update `qc-run.yaml` to look like:

```
- name: IOT_QC_RUN_BUCKET
  value: {your-bucket-name}

- name: IOT_QC_RUN_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: gcp-secret-key 
        key: {name-of-the-key-file}.json
```

## If you aren't making a new bucket, jump here

```shell
cd apps/qc-run

docker build -t qc_run:latest .

docker tag qc_run:latest harbor.axds.co/iot-data-landing/qc_run:latest
docker push harbor.axds.co/iot-data-landing/qc_run:latest

kubectl apply -f qc-run.yaml
```

At this point you should be able to visit tabledap and see that new data and QC data are being populated into the datasets.