# iot-data-landing

IoT Data Landing Project

## Development Setup

Development requires existing installations of Python and Docker.

1. Clone this repository

    ```shell
    git clone git@github.com:derekcoffman/iot-data-landing.git
    ```

1. Decrypt the repository with `git crypt`. This requires [`git-crypt`](https://github.com/AGWA/git-crypt) be [installed](https://github.com/AGWA/git-crypt/blob/master/INSTALL.md) and that your gpg key be added to the repository by someone that already has unencrypted access.

    ```shell
    git-crypt unlock
    ```

1. Follow the instructions in the [Development README](dev/README.md) to start the entire stack locally in a Kubernetes cluster. If you are coming back to development and have already run those steps, make sure the `iot-data-landing` cluster is started. To start the clusert run `k3d cluster start iot-data-landing`.

    ```shell
    $ k3d cluster list

    NAME               SERVERS   AGENTS   LOADBALANCER
    iot-data-landing   1/1       1/1      true
    ```

1. Build, push, and deploy all `apps` to your k3d cluster

    ```shell
    $ make deploy
    ...
    ```

## New Collaborators

New collaborators will need to associate a GPG key with their GitHub account using the following resources:

* [Creating a GPG key](https://docs.github.com/en/authentication/managing-commit-signature-verification/generating-a-new-gpg-key)
* [Associating email with the key](https://docs.github.com/en/authentication/managing-commit-signature-verification/associating-an-email-with-your-gpg-key)

After that an existing collaborator will need to do the following:

1. Import the new collaborator's public key

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

Each thing, whether real or mocked, needs a certificate and private key to publish data to the AWS MQTT Server. To generate a new thing along with a certificate and key, run the `scripts/create_thing.sh` script and pass it the name of the thing you would like to generate.

```shell
./scripts/create_thing.sh my-first-new-thing
```

That will create or update the certificates and keys in the `things/my-first-new-thing` folder and send the first message to the AWS IoT Core MQTT endpoint to register and provision the new "thing".
