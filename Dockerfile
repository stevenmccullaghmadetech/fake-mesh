FROM python:3.7-stretch
RUN apt-get update && apt-get install -y \
    liblmdb-dev \
  && rm -rf /var/lib/apt/lists/*
COPY . /fake_mesh
RUN pip install /fake_mesh \
  && rm -dr /fake_mesh
EXPOSE 8829/tcp
VOLUME /tmp/fake_mesh_dir
CMD ["python3", "-m", "fake_mesh.server"]
