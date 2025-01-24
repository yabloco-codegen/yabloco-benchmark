# yabloco-benchmark

# Directories

### `bench`

The benchmark tables for test and dev sets accompanied by json-files with links from every function to functions that it calls (`next`). 

### `data_extraction`

The pipeline used for collecting the benchmark.

* `tables` contains tables with test coverage, json-files with function call graphs, repository statistics and a docstring labeling judgement,
* `commit_dates.py` extracts commit dates for functions from repositories,
* `db_stat.py` collects a table of functions from a function call graph,
* `merge_commits.py` merges commit dates into the tables,
* `pipeline.sh` runs aforementioned steps to produce a table for repository,
* `merge_test_cov.py` merges test coverage hits into the tables,
* `generate_benchmark.py` script produces benchmark and dev tables.

### `finetune`

Notebooks and dockerfiles used to fine-tune models on training set. Training script is based on [fsdp_qlora](https://github.com/AnswerDotAI/fsdp_qlora) project.

### `streamlit_app`

A streamlit took to evaluate models and visualize generated and original code as well as result tables. The directory contains a separate README file with instructions to run.

### `train_data`

* `prev` contains json-files with links from every function to functions that call it, produced from function call graphs,
* `train_functions` contains tables of all train functions (similar to tables in `bench`) used for fine-tuning,
* `db_stat_prev.py` script produces `prev` tables,
* `generate.py` script produces train tables.

# Cite
YABLoCo: Yet Another Benchmark for Long Context Code Generation
