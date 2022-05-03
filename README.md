# iot-data-landing
IoT Data Landing Project


## Development Setup

Development requires existing installations of Python and Docker.

1. Clone this repository

    ```bash
    $ git clone git@github.com:derekcoffman/iot-data-landing.git
    ```

1. Decrypt the repository with `git crypt`. This requires [`git-crypt`](https://github.com/AGWA/git-crypt) be [installed](https://github.com/AGWA/git-crypt/blob/master/INSTALL.md) and that your gpg key be added to the repository by someone that already has unencrypted access.

    ```bash
    $ git-crypt unlock
    ```

1. Install required Python dependencies

    ```
    $ pip install -r requirements.txt
    ```

1. Change permissions on the local TLS cert files to the uid/gid that runs mosquitto inside of the Docker container

    ```
    sudo chown 1883:1883 docker/certs/*
    ```

1. Start a local Mosquitto MQTT broker on port 1833 and 8883 (TLS)

    ```
    docker-compose up -d
    ```

1. Start the mock sever:

    ```
    python mock_sensor/mock.py
    ```
