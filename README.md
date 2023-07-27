
# This project is  no longer being actively maintained please see [mesh-sandbox](https://github.com/NHSDigital/mesh-sandbox)  which provides a locally testable version of MESH and is maintained by the MESH team  


--------------------------------------------
Fake MESH
=========

A lightweight implementation of [NHS Digital's MESH API](https://meshapi.docs.apiary.io/), for
testing purposes.

Releases
----------

0.1.6: Changed default shared key, added documentation
0.2.0: Adds a /healthcheck to aid deployment into clusters

Docker
----------

Use docker-compose to run a Fake MESH in Docker.

```
docker-compose build fake_mesh
docker-compose up fake_mesh
```

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

Healthcheck
-----------

In addition to the MESH endpoints the server runs a healthcheck endpoint

    http://HOST:8888/healthcheck

which always responds with a 200 status and empty body.

Developing
-----------

Setup PyCharm interpreter: create new virtual environment

    File -> Preferences -> Project: fake-mesh -> Project Interpreter -> [GEAR] -> Add…
    Virtualenv Environment
    Location: fake-mesh/venv
    Base interpreter: 3.8

Activate the venv and install dependencies

    $ source venv/bin/activate
    $ pip install -e .

Create a run configuration

    Run/Debug Configurations -> Add -> Python
    Choose “Module name” instead of “Script path”
    Module name: fake_mesh.server
    Python interpreter: the interpreter you just created