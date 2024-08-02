from datetime import timedelta

REPOS = ["bullet3", "llvm", "openssl", "redis"]

# paths
BENCH_PATH = "./streamlit_app"
BENCH_JS_PATH = "./bench"
RESULTS_PATH = "./streamlit_app/results"
REPOS_PATH = "./repos"

# read results cache
CACHE_TIMEOUT = 30

# background compute
UPDATE_PERIOD = 300
NUM_INSTANCES = 8  # docker containers to run simultaneously
NUM_INSTANCES_REDIS = 4  # redis fails if more than 4 containers run simultaneously
DOCKER_CHECK_PERIOD = 5

TIMEOUT = {
    "bullet3": timedelta(minutes=30),
    "llvm": timedelta(minutes=4 * 60),
    "openssl": timedelta(minutes=30),
    "redis": timedelta(minutes=30),
}
