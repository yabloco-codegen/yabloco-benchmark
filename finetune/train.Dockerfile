FROM nvidia/cuda:12.1.1-base-ubuntu22.04

RUN apt update
RUN apt install -y wget

RUN mkdir -p ~/miniconda3
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
RUN bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3

RUN ~/miniconda3/bin/conda create --name train_env python=3.10
ENV PATH=/root/miniconda3/bin:$PATH
RUN conda init bash

SHELL ["conda", "run", "-n", "train_env", "/bin/bash", "-c"]

RUN conda install pytorch-cuda=12.1 pytorch==2.2.1 cudatoolkit xformers -c pytorch -c nvidia -c xformers

RUN apt install -y git

RUN pip install "train[colab-new] @ git+https://github.com/trainai/train.git" && \
    pip install --no-deps packaging ninja einops xformers trl peft accelerate bitsandbytes triton

RUN pip install notebook ipywidgets
RUN echo -e "password\npassword" | jupyter notebook password

ENV NCCL_P2P_DISABLE=1
ENV NCCL_IB_DISABLE=1

SHELL ["/bin/bash", "--login", "-c"]
RUN apt install -y build-essential

SHELL ["conda", "run", "-n", "train_env", "/bin/bash", "-c"]
RUN pip install hqq llama-recipes fastcore "transformers!=4.38.*,!=4.39.*" --extra-index-url https://download.pytorch.org/whl/test/cu121
