FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y build-essential cmake git python3.9 nano pip
RUN python3.9 -m pip install pandas tqdm --upgrade

RUN git clone https://github.com/openssl/openssl
WORKDIR openssl

RUN git checkout d597b46f9bdb533761e36fcf1d96ce83f3f6f04d

RUN ./Configure --prefix=/openssl --openssldir=/openssl \
    '-Wl,-rpath,$(LIBRPATH)'
