FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

RUN apt update && apt install -y build-essential wget git software-properties-common python3.10-dev python3.10-distutils python3-pip

RUN python3 -m pip install --upgrade pip
RUN pip install notebook ipywidgets
RUN echo "password\npassword" | jupyter notebook password

RUN pip install torch==2.2.1 torchvision torchaudio triton packaging --index-url https://download.pytorch.org/whl/cu121
RUN pip install ninja einops trl peft accelerate bitsandbytes xformers hqq llama-recipes fastcore transformers
RUN pip install flash-attn --no-build-isolation

ENV NCCL_P2P_DISABLE=1
ENV NCCL_IB_DISABLE=1
