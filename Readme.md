# The zeroLET Task Model and its Application to Offset Design Space Exploration

The repository is used to reproduce the evaluation from

*"The zeroLET Task Model and its Application to Offset Design Space Exploration". Shumo Wang, Enrico Bini, Qingxu Deng, Martina Maggio*

This document is organized as follows:

1. [Environment Setup](#environment-setup)
2. [How to run the experiments](#how-to-run-the-experiments)
3. [Overview of the corresponding functions](#overview-of-the-corresponding-functions)
4. [Miscellaneous](#miscellaneous)

## Environment Setup

### Requirements

To run the experiments Python 3.12 is required. Moreover, the following packages are
required:

```
pip install numpy 
```

In case there is any dependent package missing, please install them accordingly.

### File Structure

```
├── data                         # Experiment results (Python)
├── data_c                       # Experiment results (C)
├── analysis_zero_let.py         # ZeroLET analysis implementation (Python)
├── evaluation_zero_let.py       # Experiment runner (Python)
├── analysis_zero_let.c          # ZeroLET analysis implementation (C)
├── evaluation_zero_let.c        # Experiment runner (C)
├── extremes_zero_let.c          # Extremes evaluation (C)
└── README.md  
```

### Deployment

The following steps explain how to deploy this framework on the machine:

First, clone the git repository or download
the [zip file](https://github.com/wsm6636/ZEROLET/archive/refs/heads/main.zip):

```
git clone https://github.com/wsm6636/ZEROLET.git
```

### Quick Start

#### Python version

Move into the code folder and execute evaluation_zero_let.py natively:

```
cd ZEROLET
python evaluation_zero_let.py
```

Key Parameters:

| Argument | Description | Default |
|---|---|---|
| `--mode` | `extremes`, `runtime`, or `all` | `all` |
| `--perioddown` | minimum task period | `2` |
| `--periodup` | maximum task period | `12` |
| `--num_chains_extreme` | chain length of extremes | `3` |
| `--num_limit` | minimum chain length | `3` |
| `--num_chains` | maximum chain length | `6` |
| `--num_repeats` | repetitions for runtime evaluation | `100` |


The results are output and saved in data/.

The usage examples and running time of run_experiments.sh are as follows:
As a reference, we utilize a machine running Ubuntu 24.04.2 LTS (2025-09-05) x86_64 GNU/Linux, with 13th Gen Intel® Core™ i7-13700F × 24 and 32.0 GiB RAM.

Keeping `perioddown = 2, periodup = 12, num_chains_extreme = 3` in `evaluation_zero_let.py` with `--mode extremes`to obtain the same result from the paper. You can get different results by changing the bound of periods and number of tasks.

Example:

```bash
python evaluation_zero_let.py --mode extremes 
```

#### C version

Results for the C version are stored in data_c/ by default.

**Compile and run the extremes evaluation:**
```bash
gcc -std=c11 -Wall -Wextra -O2 -DZEROLET_EVALUATION_NO_MAIN analysis_zero_let.c evaluation_zero_let.c extremes_zero_let.c -lm -o extremes_zero_let_c.exe
# Run with default settings
.\extremes_zero_let_c.exe
# Or specify parameters: [perioddown] [periodup] [num_chains_extreme] [seed]
.\extremes_zero_let_c.exe 2 12 3 12345
```

**Compile and run the runtime evaluation:**
```bash
gcc -std=c11 -Wall -Wextra -O2 analysis_zero_let.c evaluation_zero_let.c -lm -o evaluation_zero_let_c.exe
# To generate RoverC and runtime result figures
.\evaluation_zero_let_c.exe
# Run with custom parameters: [num_limit] [num_chains] [num_repeats]
.\evaluation_zero_let_c.exe 3 6 1
# Run only for n=3
.\evaluation_zero_let_c.exe 3 3 1
```

### Acknowledgments

### License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
