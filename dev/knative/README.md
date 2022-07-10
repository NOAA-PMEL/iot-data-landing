# Start an example Service

1. Make sure the port forward script is running

    ```bash
    $ bash dev/ports.sh
    ```

2. Start a new Service

    ```bash
    $ kn service create hello \
    --image gcr.io/knative-samples/helloworld-go \
    --port 8080 \
    --env TARGET=World
    ```

3. List the Knative Services

    ```bash
    $ kn service list

    NAME    URL                                LATEST        AGE   CONDITIONS   READY   REASON
    hello   http://hello.default.example.com   hello-00001   18m   3 OK / 3     True
    ```

4. Access the service by setting the `Host` header to the `URL` of your Knative Service and accessing the Knative loadbalancer on `http://localhost:8083`

    ```bash
    $ curl -H "Host: hello.default.example.com" http://localhost:8083
    Hello World!
    ```

5. To watch a Service's Pods scale up and down as they are accessed you can run

    ```bash
    $ kubectl get pod -l serving.knative.dev/service=hello -w
    NAME                                      READY   STATUS              RESTARTS   AGE
    hello-00001-deployment-68cbbf7f84-cnhmh   2/2     Running             0          45s
    hello-00001-deployment-68cbbf7f84-cnhmh   2/2     Terminating         0          63s
    hello-00001-deployment-68cbbf7f84-hwkrc   0/2     Pending             0          0s
    hello-00001-deployment-68cbbf7f84-hwkrc   0/2     Pending             0          0s
    hello-00001-deployment-68cbbf7f84-hwkrc   0/2     ContainerCreating   0          0s
    hello-00001-deployment-68cbbf7f84-hwkrc   1/2     Running             0          2s
    hello-00001-deployment-68cbbf7f84-hwkrc   2/2     Running             0          2s
    hello-00001-deployment-68cbbf7f84-cnhmh   0/2     Terminating         0          95s
    hello-00001-deployment-68cbbf7f84-cnhmh   0/2     Terminating         0          95s
    hello-00001-deployment-68cbbf7f84-cnhmh   0/2     Terminating         0          95s
    ```
