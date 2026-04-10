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
from collections import defaultdict
import csv
import datetime
import itertools
from analysis_zero_jitter_order import run_analysis_zero_jitter_order, run_analysis_zero_jitter_original, compute_four_latencies_zero_jitter
import random
import time
import os
from analysis_passive import Task


def output_zero_jitter_order(random_seed, timestamp, period_stats,perioddown, periodup,num_chains):
    folder_path = "order/zero_jitter/all_periods_offsets_combinations"
    os.makedirs(folder_path, exist_ok=True)

    results_csv = os.path.join(folder_path, f"data_{perioddown}_{periodup}_n{num_chains}_{random_seed}_{timestamp}.csv")

    def unpack_offset(offset_pair):
        if offset_pair is None:
            return [], []
        return offset_pair[0], offset_pair[1]

    with open(results_csv, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # 列名
        header = [
            "periods",
            "seeds", "zero_jitter", "best_latency", "(latency, count)", 'best_merge_pair'
            "sum_period",  "sum_execution_time"
        ]
        for typ in ["LF", "FF", "LL", "FL"]:
            for ext in ["max", "min"]:
                header.extend([
                    f"{ext}_diff_sync_{typ}",
                    f"{ext}_sync_original_{typ}",         
                    f"{ext}_sync_zero_jitter_{typ}",     
                    f"{ext}_offset_{typ}_read",
                    f"{ext}_offset_{typ}_write"
                ])
        writer.writerow(header)

        for period_key, stats in period_stats.items():
            row = [str(list(period_key))]

            meta = stats['representative_meta']
            if meta:
                row.extend([
                    meta['seed'],
                    meta['zero_jitter'],
                    meta['best_latency'],
                    meta['count_result'],
                    meta['best_merge_pair'],
                    meta['sum_period'],
                    meta['sum_execution_time']
                ])
            else:
                row.extend([None] * 7)

            for typ in ["LF", "FF", "LL", "FL"]:
                for ext in ["max", "min"]:
                    rec = stats[f'{ext}_{typ}']
                    if rec['diff'] in (float('inf'), float('-inf')):
                        row.extend([None, None, None, [], []])
                    else:
                        r_off, w_off = unpack_offset(rec['offset'])
                        row.extend([
                            rec['diff'],
                            str(rec['orig_list']),    
                            str(rec['zj_list']),     
                            r_off,
                            w_off
                        ])

            writer.writerow(row)


    print(f"All results saved to {results_csv}")

    return results_csv


def generate_all_rw_combinations(periods):
    per_task_options = []
    for P in periods:
        options = []
        for r in range(0, P):                     # r ∈ [0, P)
            for w in range(r + 1, r + P + 1):     # w ∈ (r, r + P] → integers: r+1 to r+P inclusive
                options.append((r, w))
        per_task_options.append(options)
    
    all_combinations = []
    for combo in itertools.product(*per_task_options):
        reads = tuple(pair[0] for pair in combo)
        writes = tuple(pair[1] for pair in combo)
        all_combinations.append((reads, writes))
    
    return all_combinations


def generate_period_combinations(perioddown, periodup,num_chains):
    periods = list(range(perioddown, periodup + 1))
    
    combinations = list(itertools.product(periods, repeat=num_chains))
    
    return combinations



def run_evaluation_zero_jitter_order_check_offset(jitters, num_chains, num_repeats, random_seed, perioddown, periodup):

    period_stats = defaultdict(lambda: {
        'representative_meta': None,
        'max_LF': {'diff': float('-inf'), 'orig': None, 'zj': None, 'offset': None},
        'min_LF': {'diff': float('inf'),  'orig': None, 'zj': None, 'offset': None},
        'max_FF': {'diff': float('-inf'), 'orig': None, 'zj': None, 'offset': None},
        'min_FF': {'diff': float('inf'),  'orig': None, 'zj': None, 'offset': None},
        'max_LL': {'diff': float('-inf'), 'orig': None, 'zj': None, 'offset': None},
        'min_LL': {'diff': float('inf'),  'orig': None, 'zj': None, 'offset': None},
        'max_FL': {'diff': float('-inf'), 'orig': None, 'zj': None, 'offset': None},
        'min_FL': {'diff': float('inf'),  'orig': None, 'zj': None, 'offset': None},
    })
    
    all_period_combinations = generate_period_combinations(perioddown, periodup,num_chains)

    for i in range(num_repeats):            # loop on number of repetitions
        random.seed(random_seed)
        for period_combo in all_period_combinations:
            
            all_rw_offset_combinations = generate_all_rw_combinations(period_combo)
            
            for idx, (read_offsets_tuple, write_offsets_tuple) in enumerate(all_rw_offset_combinations):
                selected_periods = list(period_combo)
                selected_read_offsets = list(read_offsets_tuple)
                selected_write_offsets = list(write_offsets_tuple)
                

                # for num_tasks in num_chains:        # on number of tasks in a chain
                for per_jitter in jitters:      # on relative (to period) magnitude of jitter
                    # generate the jitter
                    # only generate the jitter
                    print(f"================== Combination {idx+1}/{len(all_rw_offset_combinations)}: periods {selected_periods}, read_offsets {selected_read_offsets}, write_offsets {selected_write_offsets}, random_seed {random_seed} ==================")
                    original_latencies = run_analysis_zero_jitter_original(num_chains, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter)

                    zerojitter_final, best_result, count_result, sum_period = run_analysis_zero_jitter_order(num_chains, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter)

                    best_latency = best_result[0]
                    best_merge_pair = best_result[1]
                    best_task = best_result[2]
                    # print(f"latencies: best_task")
                    zero_jitter_latencies = compute_four_latencies_zero_jitter(best_task)

                    # print(f"latencies: zero_jitter_task")
                    zerojitter = zerojitter_final[0] if zerojitter_final else None
                    zero_jitter_task = Task(read_event=zerojitter_final[1], write_event=zerojitter_final[2], id=zerojitter_final[1].id)
                    compute_four_latencies_zero_jitter(zero_jitter_task)

                    # print(f"best_merge_pair: {best_merge_pair}")

                    sum_execution_time = sum(w - r for w, r in zip(selected_write_offsets, selected_read_offsets))
                    sync_original = [l - sum_execution_time for l in original_latencies]
                    sync_zero_jitter = [l - sum_execution_time for l in zero_jitter_latencies]
                    diff_sync = [zj - orig for zj, orig in zip(sync_zero_jitter, sync_original)]

                    meta = {
                        'seed': random_seed,
                        'zero_jitter': zerojitter,
                        'best_latency': best_latency,
                        'count_result': str([(item["latency"], item["count"]) for item in count_result]),
                        'best_merge_pair': best_merge_pair,
                        'sum_period': sum_period,
                        'sum_execution_time': sum_execution_time,
                    }

                    period_key = tuple(selected_periods)
                    stats = period_stats[period_key]

                    # 仅在第一次遇到该 period_key 时保存 representative_meta
                    if stats['representative_meta'] is None:
                        stats['representative_meta'] = meta

                    delay_types = [('LF', 0), ('FF', 1), ('LL', 2), ('FL', 3)]
                    for name, idx in delay_types:
                        d_val = diff_sync[idx]
                        orig_list = sync_original
                        zj_list = sync_zero_jitter
                        offset = (selected_read_offsets, selected_write_offsets)

                        if d_val > stats[f'max_{name}']['diff']:
                            stats[f'max_{name}'] = {
                                'diff': d_val,
                                'orig_list': orig_list,
                                'zj_list': zj_list,
                                'offset': offset
                            }
                        if d_val < stats[f'min_{name}']['diff']:
                            stats[f'min_{name}'] = {
                                'diff': d_val,
                                'orig_list': orig_list,
                                'zj_list': zj_list,
                                'offset': offset
                            }


        random_seed = random_seed+1

    return dict(period_stats)




if __name__ == "__main__":
    num_repeats = 1 
    
    periods = [5,3,4]

    jitters = [0]

    num_chains = 3
    perioddown = 3
    periodup = 4

    # offset_ranges = [range(p) for p in periods]  
    # all_read_offset_combinations = list(itertools.product(*offset_ranges))
    # total_combos = len(all_read_offset_combinations)  
    
    # random_seed = 1755016037  # fixed seed
    # timestamp = datetime.datetime.fromtimestamp(int(time.time())).strftime("%Y%m%d_%H%M%S")

    random_seed = int(time.time())
    timestamp = datetime.datetime.fromtimestamp(random_seed).strftime("%Y%m%d_%H%M%S")
    
    stats  = run_evaluation_zero_jitter_order_check_offset(jitters, num_chains, num_repeats, random_seed, perioddown, periodup)

    output_zero_jitter_order(random_seed, timestamp, stats , perioddown, periodup,num_chains)

