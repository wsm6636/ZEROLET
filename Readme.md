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

### Figure 8: Reference Environment and Computational Limits

The **Figure 8** experiment was run with the C implementation available in the
[`emsoft2026` version](https://github.com/wsm6636/ZEROLET/tree/emsoft2026).
This branch contains the earlier Python implementation; the configuration below
documents the reference C experiment and does not replace this branch's Python
requirements or the separate environment example above.

We ran the experiment for approximately one day on a machine with the following
configuration to obtain the results shown in **Figure 8**:

- **OS**: Ubuntu 22.04.5 LTS (Jammy Jellyfish).
- **Kernel**: Linux 6.8.0-124-generic x86_64.
- **Architecture**: x86_64.
- **CPU**: 2 × Intel(R) Xeon(R) Gold 6226R CPU @ 2.90 GHz.
- **CPU cores/threads**: 32 physical cores, 64 hardware threads in total.
- **Memory**: 503 GiB RAM.
- **Disk**: 916 GB filesystem, with 147 GB available during testing.
- **GCC**: `gcc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0`.
- **Python**: Python 3.10.12 (used for the C version's optional plotting helper).

This duration is a reference measurement, not a guaranteed execution time on
other machines.

In the C version, the threshold definitions in `evaluation_zero_let.c`
(lines 21–26) are used by the Linux parallel runtime evaluator to constrain the
computational complexity and offset search space of sampled task chains, keeping
the workload within the resources of the reference machine. The active
thresholds are `ZEROLET_C_LIMIT = 1000000000000LL` and
`ZEROLET_OFFSET_SPACE_LIMIT = 50000000LL`; the smaller values in that block are
commented-out alternatives. This Python branch instead applies the condition
`C <= 1e9 and space_size <= 1e5` in `evaluation_zero_let.py`.

For a quicker exploratory run of the C version, you may reduce its thresholds
and recompile the parallel evaluator. Such runs can be used to examine
qualitative trends, but lower thresholds change the set of admissible task
chains, so similar trends are not guaranteed and numerical results may differ
from Figure 8. To attempt to reproduce Figure 8, use the C version with the
reference thresholds and the reproduction parameters documented in its README.

### Acknowledgments

### License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
