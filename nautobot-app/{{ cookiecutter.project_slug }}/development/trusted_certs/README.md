# Trusted Certificates

Include all the trusted certificates (*.crt) that you want to be installed in the Nautobot container.
These certificates will be installed in the `/usr/local/share/ca-certificates` directory and
then the `update-ca-certificates` command will be run to update the certificate store.
