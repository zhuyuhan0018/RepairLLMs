"""
Configuration file for the Reverse-Engineered Reasoning for Code Repair system
"""
import os

# Model paths
LOCAL_MODEL_PATH = "/mnt/nvme/quan/LLM-Models/qwen2-5-32b-instruct/"
ALIYUN_API_KEY = "sk-6f811b7e2654469fb1760b9b87e174c7"
# Leave empty to use dashscope defaults; set to override base endpoint if needed.
ALIYUN_API_BASE = ""

# Generation parameters
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))  # Maximum iterations for each fix point
MAX_GREP_ATTEMPTS = 3  # Maximum grep command attempts per iteration
TEMPERATURE = 0.7
MAX_TOKENS = 2048
# Cloud generation cap to reduce latency (runtime knob)
# Set to 1200 tokens to prevent response truncation while maintaining reasonable API call time
CLOUD_MAX_TOKENS = int(os.getenv("CLOUD_MAX_TOKENS", "1200"))

# Perplexity optimization
PERPLEXITY_THRESHOLD = 3.0  # Threshold for replacing high perplexity content
MIN_REPLACEMENT_LENGTH = 50  # Minimum length of content to replace

# Skip local model / perplexity stage (set env SKIP_LOCAL=1 to enable)
SKIP_LOCAL = os.getenv("SKIP_LOCAL", "0") == "1"

# Step-by-step debugging controls (set env variables to skip specific steps)
# SKIP_REPAIR_ORDER=1: Skip repair order analysis (use existing fix_points if available)
# SKIP_INITIAL_FIX=1: Skip initial fix generation (only do validation/iteration)
# SKIP_VALIDATION=1: Skip validation and iteration (only generate initial fix)
# SKIP_MERGE=1: Skip merging thinking chains (use simple concatenation instead)
SKIP_REPAIR_ORDER = os.getenv("SKIP_REPAIR_ORDER", "0") == "1"
SKIP_INITIAL_FIX = os.getenv("SKIP_INITIAL_FIX", "0") == "1"
SKIP_VALIDATION = os.getenv("SKIP_VALIDATION", "0") == "1"
SKIP_MERGE = os.getenv("SKIP_MERGE", "0") == "1"

# Output paths
OUTPUT_DIR = "./outputs"
THINKING_CHAINS_DIR = os.path.join(OUTPUT_DIR, "thinking_chains")
OPTIMIZED_CHAINS_DIR = os.path.join(OUTPUT_DIR, "optimized_chains")
LOGS_DIR = "./logs"

# Create output directories
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(THINKING_CHAINS_DIR, exist_ok=True)
os.makedirs(OPTIMIZED_CHAINS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

