## Docker images

```bash
> cd docker
> docker build -f bullet3.Dockerfile -t bullet3 .
> docker build -f llvm.Dockerfile -t llvm .
> docker build -f openssl.Dockerfile -t openssl .
> docker build -f redis.Dockerfile -t redis .
```

## Streamlit app and Background compute
### Configure `config.py`
* BENCH_PATH - folder where to search for benchmark abd generations
  * Example of usage: BENCH_PATH/bench-v0.6/bench-v0.6.csv
  * Example of usage: BENCH_PATH/bench-v0.6/CodeLlama-13B.csv
* BENCH_JS_PATH - folder where to search for next.json, which stores the callees for every function
  * Example of usage: BENCH_JS_PATH/bench-v0.6.json
* RESULTS_PATH - folder where to store the test results
* REPOS_PATH - should store the repositories in specific commits:
```
git clone https://github.com/bulletphysics/bullet3
cd bullet3 && git checkout 6bb8d1123d8a55d407b19fd3357c724d0f5c9d3c
cd ..
git clone https://github.com/llvm/llvm-project
cd llvm-project && git checkout 5b015229b77d6ea7916a503d88661b04d4867e7c
cd ..
git clone https://github.com/redis/redis
cd redis && git checkout 493e31e3ad299c99cbb96b8581b7598b19b23892
cd ..
git clone https://github.com/openssl/openssl
!cd openssl && git checkout d597b46f9bdb533761e36fcf1d96ce83f3f6f04d
cd ..
```

## To run:
* `python background_compute.py`
* `streamlit run .\streamlit_app.py`