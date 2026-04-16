#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 05 10:25:52 2026

It implements the methods described in the paper
    "The zeroLET Task Model and its Application to
    Offset Design Space Exploration". 
    Shumo Wang, Enrico Bini, Qingxu Deng, Martina Maggio, 
    IEEE/ACM International Conference on Embedded Software (EMSOFT), 2026

@author: Shumo Wang
"""
import csv
import datetime

import itertools
import random
import time
import os
import numpy as np

import math

from analysis_zero_let import run_analysis_zero_let


def generate_period_combinations(perioddown, periodup,num_chains):
    """
    Generates all possible combinations of periods.
    For example: period range [2, 3], task chain length 2 -> [(2,2), (2,3), (3,2), (3,3)]
    """
    periods = list(range(perioddown, periodup + 1))
    
    combinations = list(itertools.product(periods, repeat=num_chains))
    
    return combinations


def generate_all_read_combinations_zero(periods):
    """
    Generates all possible Read Offsets for a given set of periods.
    According to the zeroLET model, the offset for the first task is fixed at 0, 
    while the offsets for subsequent tasks lie within the range [0, P_i].
    """
    if not periods:
        return [()]
    
    ranges = []
    
    ranges.append([0])
    
    for P in periods[1:]:
        ranges.append(range(P+1))
    
    return list(itertools.product(*ranges))


def isMaxHarmonic(periods):
    """
    Determines whether a set of periods is "Max-Harmonic."
    That is: Can the maximum value within the set of periods be evenly divisible by all other periods?
    """
    if not periods:
        return 0

    maxPeriod = max(periods) if periods else 0

    for p in periods:
        if p == 0 or maxPeriod % p != 0:
            return 0

    return 1



def run_evaluation_and_track_extremes(num_chains, random_seed, perioddown, periodup):
    """
    Core Evaluation Function: Iterates through all period combinations and, for each combination, 
    identifies the offset configurations that yield the minimum and maximum delays.
    """
    all_period_combinations = generate_period_combinations(perioddown, periodup, num_chains)
    random.seed(random_seed)
    
    period_stats_map = {}
    
    total_combos = len(all_period_combinations)
    
    print(f"Starting evaluation for {total_combos} period combinations...")

    for p_idx, period_combo in enumerate(all_period_combinations):
        p_key = tuple(period_combo)
        
        if p_key not in period_stats_map:
            period_stats_map[p_key] = {
                'min_record': None,  
                'max_record': None  
            }
        
        all_read_combinations = generate_all_read_combinations_zero(period_combo)
        total_offsets = len(all_read_combinations)
        
        print(f"[{p_idx+1}/{total_combos}] Processing Periods: {period_combo} ({total_offsets} offset combos)...")

        current_seed = random_seed + p_idx 
        
        for idx, read_offsets_tuple in enumerate(all_read_combinations):
            selected_periods = list(period_combo)
            selected_read_offsets = list(read_offsets_tuple)
            selected_write_offsets = selected_read_offsets  

            try:
                histogram, latency_list, H, stats = run_analysis_zero_let(
                    num_chains, selected_periods, selected_read_offsets, selected_write_offsets, 0
                )
            except Exception as e:
                print(f"Error processing {selected_periods} with offsets {selected_read_offsets}: {e}")
                continue

            current_max_latency = stats["max"]
            
            current_record = {
                "seed": current_seed + idx,
                "periods": selected_periods,
                "read_offsets": selected_read_offsets,
                "write_offsets": selected_write_offsets,
                "stats": stats,
                "histogram": histogram,
                "diff": sum(selected_periods) - current_max_latency
            }

            min_rec = period_stats_map[p_key]['min_record']
            if min_rec is None or current_max_latency < min_rec["stats"]["max"]:
                period_stats_map[p_key]['min_record'] = current_record

            max_rec = period_stats_map[p_key]['max_record']
            if max_rec is None or current_max_latency > max_rec["stats"]["max"]:
                period_stats_map[p_key]['max_record'] = current_record

    return period_stats_map



def output_zero_let_min_max_extremes(timestamp, period_stats_map, num_chains, perioddown, periodup):
    """
    Exports the experimental results to a CSV file.
    """
    folder_path = "data"
    os.makedirs(folder_path, exist_ok=True)

    filename = f"data_zero_let_n{num_chains}_{perioddown}_{periodup}_EXTREMES_{timestamp}.csv"
    results_csv = os.path.join(folder_path, filename)

    print(f"Writing extreme values to {results_csv}...")

    with open(results_csv, mode='w', newline='') as file:
        writer = csv.writer(file)

        header = [
            "$T_i$ period", 
            "$L_\mathcal{Z}^-$ minimum offset-free reaction time", 
            "$\phase{\zeta_i} of L_\mathcal{Z}^-$ offset of minimum (One of offsets can be obtained the minimum values)", 
            "$L_\mathcal{Z}^+$ maximum offset-free reaction time", 
            "$\phase{\zeta_i} of L_\mathcal{Z}^+$ offset of maximum (One of offsets can be obtained the maximum values)", 
            "$L_\mathcal{Z}^+ - L_\mathcal{Z}^-$ different between maximum and minimum",
            "is max-harmonic"
        ]

        writer.writerow(header)

        sorted_keys = sorted(period_stats_map.keys())

        for p_key in sorted_keys:
            data = period_stats_map[p_key]
            min_rec = data['min_record']
            max_rec = data['max_record']

            if not min_rec or not max_rec:
                continue

            p_str = str(min_rec["periods"])
            val_min_max = min_rec["stats"]["max"]
            ro_min = str(min_rec["read_offsets"])

            val_max_max = max_rec["stats"]["max"]
            ro_max = str(max_rec["read_offsets"])

            diff_val = val_max_max - val_min_max

            current_periods = list(p_key)
            harmonic_status = isMaxHarmonic(current_periods)

            writer.writerow([
                p_str,
                val_min_max, ro_min,
                val_max_max, ro_max, 
                diff_val, harmonic_status
            ])

    print(f"Extreme values successfully saved to {results_csv}")
    return results_csv




if __name__ == "__main__":

    perioddown = 2
    periodup =12

    num_chains = 3 
    
    random_seed = 1755016037  # fixed seed
    timestamp = datetime.datetime.fromtimestamp(int(time.time())).strftime("%Y%m%d_%H%M%S")

    results = run_evaluation_and_track_extremes(num_chains, random_seed, perioddown, periodup)
    output_zero_let_min_max_extremes(timestamp, results, num_chains, perioddown, periodup)    


