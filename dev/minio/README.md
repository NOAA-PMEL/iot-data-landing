## User/Pass Access

**User**
$ kubectl get secret minio -o jsonpath="{.data.MINIO_ROOT_USER}" | base64 --decode ; echo

**Pass**
$ kubectl get secret minio -o jsonpath="{.data.MINIO_ROOT_PASSWORD}" | base64 --decode ; echo
