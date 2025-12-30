# Reverse-Engineered Reasoning for Code Repair

This project implements a system for generating deep reasoning chains for code repair tasks using the Reverse-Engineered Reasoning (REER) paradigm, inspired by the DeepWriter approach.

## Overview

The system works "backwards" from known good solutions (fixed code) to computationally discover the latent, step-by-step deep reasoning process that could have produced them. This approach is particularly effective for open-ended tasks like code repair where clear reward signals are unavailable.

## Features

- **Initial Chain Construction**: Uses advanced cloud models (Aliyun) to construct initial thinking chains
- **Iterative Refinement**: Supports iterative generation, analysis, and reflection
- **Grep Integration**: Allows models to request and use grep commands for codebase analysis
- **Perplexity-Based Optimization**: Uses local models to optimize thinking chains by replacing high perplexity segments
- **Multi-Point Repair**: Handles complex repairs across multiple functions/files

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Edit `config.py` to configure:
- Local model path
- Aliyun API key
- Generation parameters
- Perplexity thresholds

## Usage

### Basic Usage

```python
from core.repair_pipeline import RepairPipeline

pipeline = RepairPipeline(codebase_path=".")

result = pipeline.process_repair_case(
    buggy_code="...",
    fixed_code="...",
    bug_location="file.c:function_name",
    case_id="case_001"
)
```

### Command Line Usage

```bash
# Process from JSON file
python main.py --input cases.json --input-type json --codebase-path /path/to/codebase

# Process from database
python main.py --input datasets/repairs.db --input-type database --limit 10

# Process single case
python main.py --input single_case.json --input-type single
```

### Example

See `example_usage.py` for detailed examples.

## Architecture

### Components

1. **Models** (`models/`)
   - `aliyun_model.py`: Wrapper for Aliyun Cloud API
   - `local_model.py`: Wrapper for local Qwen2 model

2. **Core** (`core/`)
   - `initial_chain_builder.py`: Constructs initial thinking chains
   - `perplexity_optimizer.py`: Optimizes chains using perplexity analysis
   - `repair_pipeline.py`: Main pipeline orchestrator

3. **Utils** (`utils/`)
   - `grep_tool.py`: Safe grep command execution
   - `prompts.py`: Prompt templates for all stages

4. **Data** (`data_loader.py`)
   - Loads repair cases from various sources

## Workflow

1. **Repair Order Analysis**: Identifies fix points and their logical order
2. **Fix Point Processing**: For each fix point:
   - Generate initial analysis
   - Optionally request grep commands
   - Validate fixes against ground truth
   - Iteratively refine based on feedback
3. **Chain Merging**: Combines individual chains into complete reasoning
4. **Perplexity Optimization**: Replaces high perplexity segments with clearer alternatives

## Output

The system generates:
- Initial thinking chains (saved to `outputs/thinking_chains/`)
- Optimized thinking chains (saved to `outputs/optimized_chains/`)

Each output includes:
- Complete thinking chain
- Fix point analysis
- Individual fix point chains
- Metadata

## Notes

- All prompts are in English
- The system maintains a "continuous reflection" illusion for the model
- Critical parts (like code fixes) are preserved during optimization
- Grep commands are executed safely with timeouts and validation

## References

- REER Paper: Reverse-Engineered Reasoning for Open-Ended Generation
- REER Code: https://github.com/multimodal-art-projection/REER_DeepWriter

## License

[Your License Here]

