FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y build-essential  git pkg-config tcl ninja-build make  python3.9 nano pip
RUN pip3 install cmake pandas tqdm --upgrade

RUN git clone https://github.com/llvm/llvm-project
WORKDIR llvm-project

RUN git checkout 5b015229b77d6ea7916a503d88661b04d4867e7c

RUN cmake -S llvm -DCMAKE_BUILD_TYPE="Release" -DLLVM_ENABLE_ASSERTIONS=On
RUN make check-llvm
