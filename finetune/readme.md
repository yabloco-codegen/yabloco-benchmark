* `cd notebooks && git clone https://github.com/AnswerDotAI/fsdp_qlora.git`
* `mv yabloco_train.py fsdp_qlora/yabloco_train.py`


* Training (change paths to yours)
```
docker run -p 8889:8888 \
    -v "train/cache:/root/.cache/huggingface" \
    -v "train/notebooks:/notebooks" \
    -v "train_data:/train_data" \
    -v "pipeline/bench:/bench" \
    -v "pipeline/repos:/repos" \
    -v "streamlit_app:/streamlit_app" \
    --gpus all --rm --name train -d train \
    conda run -n train_env jupyter notebook --ip=0.0.0.0 --allow-root --no-browser'
```
* Inference (change paths to yours)
```
docker run -p 8888:8888 \
    -v "train/cache:/root/.cache/huggingface" \
    -v "train/notebooks:/notebooks" \
    -v "train_data:/train_data" \
    -v "pipeline/bench:/bench" \
    -v "pipeline/repos:/repos" \
    -v "streamlit_app:/streamlit_app" \
    --gpus all --rm --name flashatt -d flashatt \
    jupyter notebook --ip=0.0.0.0 --allow-root --no-browser'
```
* Open "http://localhost:8888" (inference) or "http://localhost:8889" (training) to continue
