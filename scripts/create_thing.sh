#!/bin/bash

# CommonName of the "Thing"
NAME=$1

# Root dir of project
BASE=$(dirname "$(readlink -f $(dirname "$0"))")

# Directory of the thing
THING_DIR=${BASE}/things/${NAME}
mkdir -p "${THING_DIR}"

# CA to use to sign the certificate
CA_NAME=${2:-ca-aws-001}
CA_DIR=${BASE}/CAs/${CA_NAME}
if [! -d "$CA_DIR"]; then
    echo "No CA directory for ${CA_NAME} found at ${CA_DIR}"
    exit 1
fi

echo "Creating certificate and key for thing '${NAME}'"

openssl genrsa -out "${THING_DIR}/thing.key" 2048

openssl req -new \
    -key "${THING_DIR}/thing.key" \
    -out "${THING_DIR}/thing.csr" \
    -subj "/C=US/ST=WA/L=Seattle/O=NOAA/OU=PMEL/CN=${NAME}/emailAddress=kyle@axiomdatascience.com"

openssl x509 -req \
    -in "${THING_DIR}/thing.csr" \
    -CA "${CA_DIR}/ca.crt" \
    -CAkey "${CA_DIR}/ca.key" \
    -CAcreateserial \
    -out "${THING_DIR}/thing.crt" \
    -days 8000 \
    -sha256

cat "${THING_DIR}/thing.crt" "${CA_DIR}/ca.crt" > "${THING_DIR}/thing_ca.crt"


echo "Registring with IoT Core..."
mosquitto_pub \
    --cafile "${BASE}/CAs/aws-iot-core/root.crt" \
    --cert "${THING_DIR}/thing_ca.crt" \
    --key "${THING_DIR}/thing.key" \
    -h a2zlmiohh2c1vo-ats.iot.us-east-1.amazonaws.com \
    -p 8883 \
    -q 1 \
    -t foo/bar \
    -i ${NAME} \
    -m "Poke" \
    -d
