#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 05 10:25:52 2025

It implements the methods described in the paper
    "Jitter Propagation in Task Chains". 
    Shumo Wang, Enrico Bini, Qingxu Deng, Martina Maggio, 
    IEEE Real-Time Systems Symposium (RTSS), 2025

@author: Shumo Wang
"""
import csv
import datetime

import random
import time
import os
import numpy as np

from evaluation_passive import generate_periods_and_offsets
from analysis_zero_jitter import run_analysis_zero_jitter


def output_zero_jitter(num_repeats, random_seed, timestamp, results, num_chains, jitters):
    folder_path = "zero_jitter"
    os.makedirs(folder_path, exist_ok=True)

    results_csv = os.path.join(folder_path, f"data_zero_jitter_{num_repeats}_{random_seed}_{timestamp}.csv" )

    # save results to csv
    with open(results_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["seeds","num_tasks", "per_jitter", "best_latency", "run_time_zero"])
        for num_tasks in num_chains:
            for per_jitter in jitters:
                for (best_latency, seed, run_time_zero) in results[num_tasks][per_jitter]:
                    writer.writerow([seed,num_tasks, per_jitter, best_latency, run_time_zero])

    print(f"All results saved to {results_csv}")

    return results_csv


def run_evaluation_zero_jitter(jitters, num_chains, num_repeats, random_seed, periods):
    TOLERANCE = 1e-9
    # preparing list for storing result
    results = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    final = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}


    for i in range(num_repeats):            # loop on number of repetitions
        random.seed(random_seed)
        for num_tasks in num_chains:        # on number of tasks in a chain
            selected_periods, selected_read_offsets, selected_write_offsets = generate_periods_and_offsets(num_tasks, periods)
            for per_jitter in jitters:      # on relative (to period) magnitude of jitter
                # generate the jitter
                # only generate the jitter
                print(f"================== num_tasks {num_tasks} per_jitter {per_jitter} Repeat {i} random_seed {random_seed} ==================")
                t_zero_0 = time.perf_counter()
                best_latency, final_r, final_w = run_analysis_zero_jitter(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter)
                t_zero_1 = time.perf_counter()
                run_time_zero = t_zero_1 - t_zero_0

                results[num_tasks][per_jitter].append((best_latency, random_seed,run_time_zero))
                final[num_tasks][per_jitter].append((final_r, final_w))

        random_seed = random_seed+1
    return results, final




if __name__ == "__main__":
    num_repeats = 100 
    
    periods = [1, 2, 5, 10, 20, 50, 100, 200, 1000]  # periods
    
    # jitters = [0,0.02,0.05,0.1,0.2,0.3,0.4,0.5]  # maxjitter = percent jitter * period
    jitters = [0]

    num_chains = [3,5,8,10] 
    # num_chains = [3,5]
    
    random_seed = 1755016037  # fixed seed
    timestamp = datetime.datetime.fromtimestamp(int(time.time())).strftime("%Y%m%d_%H%M%S")

    # random_seed = int(time.time())
    # timestamp = datetime.datetime.fromtimestamp(random_seed).strftime("%Y%m%d_%H%M%S")

    results, final = run_evaluation_zero_jitter(jitters, num_chains, num_repeats, random_seed, periods)
    output_zero_jitter(num_repeats, random_seed, timestamp, results, num_chains, jitters)

    

