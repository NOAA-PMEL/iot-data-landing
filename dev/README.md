# Local Development Setup

## Install k3d

https://k3d.io/

## Start existing cluster

```shell
# Start cluster
$ k3d cluster start iot-data-landing

# Get and set registry port
$ docker ps -f name=iot-data-landing-registry -l --format {{.Ports}}
0.0.0.0:39727->5000/tcp
$ export DOCKER_REPO_URL="k3d-registry.localhost:39727"

# Setup kubectl
$ export KUBECONFIG=$(k3d kubeconfig write iot-data-landing)

# Deploy `apps` folder
$ make deploy
```

## Create new cluster

This cluster uses a persistent volume at `./dev/pvc/data` and forwards local ports `8080` and `8443` to the cluster's Traefik load balancer. The load balancer isn't currently used, but may be in the future.

```shell
$ k3d cluster create iot-data-landing \
    --volume $(pwd)/dev/pvc/data:/data \
    --port 8080:80@loadbalancer \
    --port 8443:443@loadbalancer \
    --registry-create iot-data-landing-registry \
    --servers 1 \
    --agents 1

$ export KUBECONFIG=$(k3d kubeconfig write iot-data-landing)
$ kubectl get node

NAME                            STATUS   ROLES                  AGE   VERSION
k3d-iot-data-landing-agent-0    Ready    <none>                 3h10m   v1.22.7+k3s1
k3d-iot-data-landing-server-0   Ready    control-plane,master   3h10m   v1.22.7+k3s1
```

This sets up a local Docker registry that you can push images to and the images can be read directly by the k3d cluster. This how local development is deployed to the k3d cluster as you are working on the code in the `apps` directory. The address of the local Docker registry can be obtained by running the following:

```shell
$ docker ps -f name=iot-data-landing-registry

CONTAINER ID   IMAGE        COMMAND                  CREATED          STATUS          PORTS                     NAMES
6ebf6c2c7863   registry:2   "/entrypoint.sh /etc…"   17 minutes ago   Up 16 minutes   0.0.0.0:40765->5000/tcp   iot-data-landing-registry
```

In this case, we can push to `k3d-registry.localhost:40765` from a local dev machine and the images will be available in the k3d cluster as well. In order for the local `apps` build process to work correctly you need to export this URL as the variable `DOCKER_REPO_URL`. Note that the port `40765` in this example may be different for you!

```shell
export DOCKER_REPO_URL="k3d-registry.localhost:40765"
```

## Install Camel-K

Camel-K can be used to translate between various sources and sinks. I've been experimenting for using it for the MQTT to Kafka bridge as it will also create the CloudEvent packets automatically. This may or may not be used in the future but it doesn't hurt to bootstrap it now.

1. [Download](https://camel.apache.org/camel-k/1.9.x/installation/installation.html#procedure) the `kamel` binary file and put it on your path.

2. Install Camel-K

    ```shell
    $ kubectl create namespace camel-k
    $ kamel install -n camel-k --force --olm=false --registry ${DOCKER_REPO_URL} --organization axds --registry-insecure true

    Camel K installed in namespace camel-k
    ```

3. Make sure Camel-K is running (this can take a few minutes)

    ```shell
    $ kubectl get pod -n camel-k

    NAME                               READY   STATUS    RESTARTS   AGE
    camel-k-operator-dc8489bfc-sdj5k   1/1     Running   0          28s
    ```

## Test PersistentStorage

The local folder `./dev/pvc/data` is the persistent volume location on the local host. This just tests the ability for the cluster to use the persistent volumes.

```shell
$ kubectl apply -f dev/pvc/storage.yaml

$ kubectl get pv
NAME             CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS   CLAIM                   STORAGECLASS   REASON   AGE
data-pv-volume   200Gi      RWO            Retain           Bound    default/data-pv-claim   local-path              7m12s

$ kubectl get pvc
NAME            STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
data-pv-claim   Bound    pvc-dac0d354-9903-435e-aaa9-0ca6f9a30209   1Gi        RWO            local-path     9s
```

Now test that you can write a file

```shell
$ kubectl exec pv-claim-test -- sh -c "echo i-wrote-something > /data/testing.txt"
$ cat ./dev/pvc/data/temp/testing.txt
i-wrote-something
```

If that works you can remove the temporary storage resources and continue on

```shell
$ kubectl delete pod pv-claim-test
$ kubectl delete pvc data-pv-claim
$ kubectl delete pv data-pv-volume
```

## Install Strimizi

https://strimzi.io/quickstarts/

```shell
$ kubectl create namespace kafka
$ kubectl create -n kafka -f 'https://strimzi.io/install/latest?namespace=kafka'
$ kubectl apply -n kafka -f dev/kafka/strimzi.yaml
$ kubectl wait kafka/iot-cluster --for=condition=Ready --timeout=300s -n kafka

kafka.kafka.strimzi.io/iot-cluster condition met
```

Test the Kafka broker

```shell
# Run in a separate terminal
$ kubectl port-forward -n kafka service/iot-cluster-kafka-bootstrap 9092
# Now test the connection
$ kafkacat -L -b localhost:9092
```

## Install Knative Operator

```shell
$ kubectl apply -f https://github.com/knative/operator/releases/download/knative-v1.4.1/operator.yaml
$ kubectl get deployment knative-operator

NAME               READY   UP-TO-DATE   AVAILABLE   AGE
knative-operator   1/1     1            1           22s
```

## Configure Knative (Serving/Eventing)

```shell
$ kubectl apply -f dev/knative/operator.yaml

namespace/knative-eventing created
namespace/knative-serving created
knativeserving.operator.knative.dev/knative-serving created
namespace/knative-eventing unchanged
knativeeventing.operator.knative.dev/knative-eventing created
```

Verify Knative Serving is running (this may take a few minutes to be READY):

```shell
$ kubectl get deployment -n knative-serving
NAME                     READY   UP-TO-DATE   AVAILABLE   AGE
activator                1/1     1            1           32s
autoscaler               1/1     1            1           32s
controller               1/1     1            1           31s
domain-mapping           1/1     1            1           31s
domainmapping-webhook    1/1     1            1           31s
webhook                  1/1     1            1           30s
autoscaler-hpa           1/1     1            1           29s
net-kourier-controller   1/1     1            1           28s
3scale-kourier-gateway   1/1     1            1           27s

$ kubectl get KnativeServing knative-serving -n knative-serving
NAME              VERSION   READY   REASON
knative-serving   1.4.0     True
```

Verify Knative Eventing is running:

```shell
$ kubectl get deployment -n knative-eventing
NAME                       READY   UP-TO-DATE   AVAILABLE   AGE
eventing-controller        1/1     1            1           2m54s
pingsource-mt-adapter      0/0     0            0           2m54s
eventing-webhook           1/1     1            1           2m54s
imc-controller             1/1     1            1           2m50s
imc-dispatcher             1/1     1            1           2m49s
mt-broker-filter           1/1     1            1           2m48s
mt-broker-ingress          1/1     1            1           2m48s
mt-broker-controller       1/1     1            1           2m47s
kafka-controller-manager   1/1     1            1           2m45s

$ kubectl get KnativeEventing knative-eventing -n knative-eventing
NAME               VERSION   READY   REASON
knative-eventing   1.4.0     True
```

## Install Knative Kafka Broker

Broker: https://knative.dev/docs/eventing/broker/kafka-broker/

```shell
$ kubectl apply -f https://github.com/knative-sandbox/eventing-kafka-broker/releases/download/knative-v1.4.0/eventing-kafka-controller.yaml
$ kubectl apply -f https://github.com/knative-sandbox/eventing-kafka-broker/releases/download/knative-v1.4.0/eventing-kafka-broker.yaml
$ kubectl apply -f dev/knative/broker.yaml

configmap/kafka-broker-config configured
broker.eventing.knative.dev/default created
configmap/config-br-defaults configured
configmap/config-kafka-broker-data-plane configured
configmap/kafka-config-logging configured
```

Make sure the Kafka broker is ready to go!

```shell
$ kn broker list

NAME      URL                                                                              AGE    CONDITIONS   READY   REASON
default   http://kafka-broker-ingress.knative-eventing.svc.cluster.local/default/default   4m4s   7 OK / 7     True
```

## Install MQTT Broker (Mosquitto)

```shell
$ kubectl apply -f dev/mqtt/

configmap/mosquitto-certs created
configmap/mosquitto-config created
deployment.apps/mosquitto created
service/mosquitto created

$ kubectl get pods --selector "app=mosquitto"

NAME                        READY   STATUS    RESTARTS   AGE
mosquitto-b5b74bc6d-lxmdk   1/1     Running   0          53m
```

Now forward the MQTT port to your host and test

```shell
# In another terminal, forward port 1883 to mosquitto
$ kubectl port-forward service/mosquitto 1883:http
# Now test the broker
$ mosquitto_pub -h "localhost" -p 1883 -q 1 -t foo/bar -i iot-mqtt-testing -m "Hello" -d

Client device-pmel-test-003 sending CONNECT
Client device-pmel-test-003 received CONNACK (0)
Client device-pmel-test-003 sending PUBLISH (d0, q1, r0, m1, 'foo/bar', ... (5 bytes))
Client device-pmel-test-003 received PUBACK (Mid: 1, RC:0)
Client device-pmel-test-003 sending DISCONNECT
```

## Install ERDDAP

```shell
$ kubectl apply -f dev/erddap

persistentvolume/erddap-data-pv-volume created
persistentvolumeclaim/erddap-data-pv-claim created
service/erddap created
deployment.apps/erddap created

# Run in a new terminal
$ kubectl port-forward service/erddap 8081:http
# Test ERDDAP by visiting http://localhost:8081
```

ERDDAP is available at [http://localhost:8081/erddap/](http://localhost:8081/erddap/)

## Install Minio

```shell
$ kubectl apply -f dev/minio

persistentvolume/minio-pv-volume created
persistentvolumeclaim/minio-pv-claim created
secret/minio created
deployment.apps/minio created
service/minio created

# Run in 2 new terminals
$ kubectl port-forward service/minio 9000:api
$ kubectl port-forward service/minio 9001:console
```

The Minio console is available at [http://localhost:9001](http://localhost:9001/) and the Minio API endpoint is available at "http://localhost:9000".

## Install Monitoring

```shell
$ helm install prometheus prometheus-community/kube-prometheus-stack

NAME: prometheus
LAST DEPLOYED: Mon Jun 27 13:53:28 2022
NAMESPACE: default
STATUS: deployed
REVISION: 1
NOTES:
kube-prometheus-stack has been installed. Check its status by running:
  kubectl --namespace default get pods -l "release=prometheus"

Visit https://github.com/prometheus-operator/kube-prometheus for instructions on how to create & configure Alertmanager and Prometheus instances using the Operator.
```

## Forward all ports

Once you have completed the above steps you can forward all ports at once using a helper script. Make sure you exit all existing `kubectl port-forward ...` commands in all terminals.

```shell
$ bash dev/ports.sh

Minio API:          http://localhost:9000
Minio Console:      http://localhost:9001
ERDDAP:             http://localhost:8081
Mosquitto (HTTP):   http://localhost:1883
          (HTTPS):  https://localhost:8883

Kafka broker:       localhost:9092

# Monitoring
Prometheus:         http://localhost:9090
Grafana:            http://localhost:3000
                    user: admin
                    pass: prom-operator
Alert Manager       http://localhost:9093

# Knative
Kourier LB (HTTP)   http://localhost:8083
           (HTTPS)  https://localhost:8483
```
