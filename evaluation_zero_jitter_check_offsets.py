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
import itertools
from analysis_zero_jitter_order import run_analysis_zero_jitter_order, run_analysis_zero_jitter_original, compute_four_latencies_zero_jitter
import random
import time
import os
import numpy as np

from evaluation_passive import generate_periods_and_offsets
from evaluation_zero_jitter_order import generate_all_rw_combinations


def output_zero_jitter_order(num_repeats, random_seed, timestamp, results,  num_tasks, jitters,periods):
    folder_path = "order/zero_jitter/per_periodset_all_offsets_combinations/"
    os.makedirs(folder_path, exist_ok=True)

    results_csv = os.path.join(folder_path, f"data_zero_jitter_offsets_{periods}_{num_repeats}_{random_seed}_{timestamp}.csv" )

    with open(results_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["period","seeds", "zero_jitter", "best_latency","(latency, count)","read_offsets","write_offsets","sum_execution_time","diff_sync","sync_original","sync_zero_jitter"])
        for num_tasks in [num_tasks]:
            for per_jitter in jitters:
                for (best_latency, seed, best_merge_pair, count_result,final, zerojitter, selected_periods, selected_read_offsets, selected_write_offsets,sum_execution_time, diff_sync, sync_original, sync_zero_jitter   ) in results[num_tasks][per_jitter]:
                    pairs = [(item["latency"], item["count"]) for item in count_result]
                    writer.writerow([periods,seed,zerojitter, best_latency,pairs,selected_read_offsets,selected_write_offsets,sum_execution_time,diff_sync,sync_original,sync_zero_jitter])

    print(f"All results saved to {results_csv}")

    return results_csv



def run_evaluation_zero_jitter_order_check_offset(jitters, num_tasks, num_repeats, random_seed, periods):
    TOLERANCE = 1e-9
    # preparing list for storing result
    results = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in [num_tasks]}
    final_res = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in [num_tasks]}
    for i in range(num_repeats):            # loop on number of repetitions
        random.seed(random_seed)
        all_rw_offset_combinations = generate_all_rw_combinations(periods)
        for idx, (read_offsets_tuple, write_offsets_tuple) in enumerate(all_rw_offset_combinations):
            selected_periods = periods
            selected_read_offsets = list(read_offsets_tuple)
            selected_write_offsets = list(write_offsets_tuple)

            for per_jitter in jitters:      # on relative (to period) magnitude of jitter
                # generate the jitter
                # only generate the jitter
                print(f"================== Combination {idx+1}/{len(all_rw_offset_combinations)}: periods {selected_periods}, read_offsets {selected_read_offsets}, write_offsets {selected_write_offsets}, random_seed {random_seed} ==================")

                original_latencies = run_analysis_zero_jitter_original(num_chains, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter)
                final, best_result, count_result, zerojitter, sum_period, diff = run_analysis_zero_jitter_order(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter)
                
                best_latency = best_result[0]
                best_merge_pair = best_result[1]
                final_r = best_result[2].read_event
                final_w = best_result[2].write_event
                best_task = best_result[2]


                zero_jitter_latencies = compute_four_latencies_zero_jitter(best_task)

                # 计算同步差值
                sum_execution_time = sum(w - r for w, r in zip(selected_write_offsets, selected_read_offsets))
                sync_original = [l - sum_execution_time for l in original_latencies]
                sync_zero_jitter = [l - sum_execution_time for l in zero_jitter_latencies]
                diff_sync = [zj - orig for zj, orig in zip(sync_zero_jitter, sync_original)]

                results[num_tasks][per_jitter].append((best_latency, random_seed, best_merge_pair, count_result, final, zerojitter, selected_periods, selected_read_offsets, selected_write_offsets,sum_execution_time, diff_sync, sync_original, sync_zero_jitter))
                final_res[num_tasks][per_jitter].append((final_r, final_w))

        random_seed = random_seed+1

    return results, final_res



if __name__ == "__main__":
    num_repeats = 1 
    
    periods = [4,10,8]
    
    jitters = [0]

    num_chains = 3

    offset_ranges = [range(p) for p in periods]  # range(7), range(6), range(10)
    all_read_offset_combinations = list(itertools.product(*offset_ranges))
    total_combos = len(all_read_offset_combinations)  # 7*6*10 = 420
    
    # random_seed = 1755016037  # fixed seed
    # timestamp = datetime.datetime.fromtimestamp(int(time.time())).strftime("%Y%m%d_%H%M%S")

    random_seed = int(time.time())
    timestamp = datetime.datetime.fromtimestamp(random_seed).strftime("%Y%m%d_%H%M%S")
    
    results, final = run_evaluation_zero_jitter_order_check_offset(jitters, num_chains, num_repeats, random_seed, periods)

    # for num_tasks in num_chains:
    #         for per_jitter in jitters:
    #             for (best_latency, seed,run_time_order, best_merge_pair, count_result,final, zerojitter, selected_periods, selected_read_offsets, selected_write_offsets   ) in results[num_tasks][per_jitter]:
    #                 pairs = [(item["latency"], item["count"]) for item in count_result]
    #                 print(f"seeds:{seed}, num_tasks:{num_tasks}, per_jitter:{per_jitter}, zero_jitter:{zerojitter}, best_latency:{best_latency}, (latency, count):{pairs}, periods:{selected_periods}, read_offsets:{selected_read_offsets}, write_offsets:{selected_write_offsets}")

    output_zero_jitter_order(num_repeats, random_seed, timestamp, results,  num_chains, jitters, periods)