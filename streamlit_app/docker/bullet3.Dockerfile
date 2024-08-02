FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y build-essential cmake git python3.9 nano pip
RUN python3.9 -m pip install pandas tqdm --upgrade

RUN git clone https://github.com/bulletphysics/bullet3
WORKDIR bullet3

RUN git checkout 6bb8d1123d8a55d407b19fd3357c724d0f5c9d3c

RUN python3.9 -m pip install numpy --upgrade
RUN ./build_cmake_pybullet_double.sh
