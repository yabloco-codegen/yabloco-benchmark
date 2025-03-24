FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y build-essential cmake git pkg-config tcl  python3.9 nano pip
RUN python3.9 -m pip install pandas tqdm --upgrade

RUN git clone https://github.com/redis/redis
WORKDIR redis

RUN git checkout 493e31e3ad299c99cbb96b8581b7598b19b23892

RUN make
