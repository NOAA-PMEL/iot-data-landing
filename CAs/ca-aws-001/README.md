# Resources

This is a CA setp for AWS IoT with just-in-time-provisioning (JITP)

https://aws.amazon.com/blogs/iot/setting-up-just-in-time-provisioning-with-aws-iot-core/

To update the JITP configuration you can edit the `template.json` file in this repository, generate a registration config file called `provision.json`, and update the CA with the new registration config file. Because of the way the provision.json file needs to be formatted (nested levels of JSON strings) it isn't stored in the repository and is generated before updating the CA each time.

```bash
# Generate provision.json
$ python make.py

# Update CA certificate with the per registration config file provision.json
$ aws iot update-ca-certificate --certificate-id 04a6849b8d105cf5428ae69dfa178d3d8d1d54735752193693a30f6c5cf55212 --registration-config file://provision.json

# Now the changes should be reflected in the CA certificate
$ aws --profile pmel_iot iot describe-ca-certificate --certificate-id 04a6849b8d105cf5428ae69dfa178d3d8d1d54735752193693a30f6c5cf55212
```
