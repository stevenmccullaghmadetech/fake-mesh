Fake MESH
=========

A lightweight implementation of [NHS Digital's MESH API](https://meshapi.docs.apiary.io/), for
testing purposes.

Installing
----------

```
pip install fake_mesh
```

Usage
-----

Start a server with:

```
python -m fake_mesh.server
```

This will start a fake MESH instance on port 8829, using the client, server and
CA certificates that are in this repo. If you need to use the Java MESH client,
there is also an example keystore and config (`mockMesh.jks` and
`meshclient.cfg`) in the repo.

You can see the options available:

```
$ python -m fake_mesh.server -h
usage: server.py [-h] [--dir DIR] [--ca-cert CA_CERT] [--cert CERT]
                 [--key KEY] [-p PORT] [-i HOST] [-d] [--no-log]
                 [--log-file [LOG_FILE]]

Run a fake MESH server

optional arguments:
  -h, --help            show this help message and exit
  --dir DIR             Where to store the application data
  --ca-cert CA_CERT     CA certificate to validate incoming connections
                        against
  --cert CERT           SSL certificate for this server
  --key KEY             SSL private key for this server
  -p PORT, --port PORT  Port to listen on
  -i HOST, --host HOST  Host interface to bind to
  -d, --debug           Print data sent and received to stderr
  --no-log              Disable all logging
  --log-file [LOG_FILE]
                        File to use for logging - use stderr if not specified
```
