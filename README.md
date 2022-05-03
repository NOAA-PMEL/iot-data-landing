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

## New Collaborators

New collaborators will need to associate a GPG key with their GitHub account using the following resources:

* [Creating a GPG key](https://docs.github.com/en/authentication/managing-commit-signature-verification/generating-a-new-gpg-key)
* [Associating email with the key](https://docs.github.com/en/authentication/managing-commit-signature-verification/associating-an-email-with-your-gpg-key)

After that an existing collaborator will need to do the following:

1. Import the new collaborators public key

    ```bash
    curl https://github.com/[github_user].gpg | gpg --import
    ```

1. Fully trust the key

    ```bash
    $ gpg --list-keys
    $ gpg --edit-key "[the key id]"
    ...
    gpg> trust
    ...
    Your decision? 5
    Do you really want to set this key to ultimate trust? (y/N) y
    ...
    gpg> quit
    ```

1. Add the collaborators key to this repository

    ```bash
    git-crypt add-gpg-user "[email associated with the key]"
    ```

1. Submit PR with new user. The above command creates a new commit.


## Things

Each thing, whether real or mocked, needs a certificate and private key to publish data to MQTT. To generate a new thing along with a certificate and key, run the `scripts/create_thing.sh` script and pass it the name of the thing you would like to generate.

```
./scripts/create_thing.sh my-first-new-thing
```

That will create or update the certificates and keys in the `things/my-first-new-thing` folder and send the first message to the AWS IoT Core MQTT endpoint to register and provision the new "thing".
