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
├── data                         # Experiment results
├── analysis_zero_let.py         # ZeroLET analysis implementation
├── evaluation_zero_let.py       # Experiment runner
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

Move into the code folder and execute evaluation_zero_let.py natively:

```
cd ZEROLET
python evaluation_zero_let.py
```

Key Parameters:

```python
perioddown = 2
periodup = 12
num_chains = 3
```

- `[perioddown]`: downbound of periods
- `[periodup]`: upbound of periods
- `[num_chains]`: number of tasks in a chain

The results are output and saved in data/, passive/, and compare/. 

The usage examples and running time of run_experiments.sh are as follows:
As a reference, we utilize a machine running Ubuntu 24.04.2 LTS (2025-09-05) x86_64 GNU/Linux, with 13th Gen Intel® Core™ i7-13700F × 24 and 32.0 GiB RAM.

Keeping `perioddown = 2, periodup = 12, num_chains = 3` in `evaluation_zero_let.py` to obtain the same result from the paper. You can get different results by changing the bound of periods and number of tasks.

### Figure 8: Experiment Environment

The following information refers to the
[C version (`emsoft2026`)](https://github.com/wsm6636/ZEROLET/tree/emsoft2026).

We ran the experiment for approximately one day on a machine with the following
configuration to obtain the results shown in **Figure 8**:

- **OS**: Ubuntu 22.04.5 LTS (Jammy Jellyfish).
- **Kernel**: Linux 6.8.0-124-generic x86_64.
- **Architecture**: x86_64.
- **CPU**: 2 × Intel(R) Xeon(R) Gold 6226R CPU @ 2.90 GHz.
- **CPU cores/threads**: 32 physical cores, 64 hardware threads.
- **Memory**: 503 GiB RAM.
- **Disk**: 916 GB filesystem, with 147 GB available during testing.
- **GCC**: `gcc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0`.
- **Python**: Python 3.10.12.

The thresholds in `evaluation_zero_let.c` (lines 21–26) limit the computational
workload of the Linux parallel evaluator to suit the host machine's resources.
You may reduce these thresholds and recompile to obtain similar qualitative
trends more quickly, although the numerical results may differ from Figure 8.

### Acknowledgments

### License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
