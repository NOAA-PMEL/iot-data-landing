# SSL Key
kubectl create configmap ssl-key --from-file=dev/pvc/data/erddap/certs/ssl.key

# SSL Cert
kubectl create configmap ssl-cert --from-file=dev/pvc/data/erddap/certs/ssl.crt

# Server file. This is for setting up SSL on tomcat
kubectl create configmap server-file --from-file=deploy/gcp/prod/server.xml
