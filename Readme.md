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

### Acknowledgments

### License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
