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
from multiprocessing import Pool, cpu_count
import random
import time
import os
from matplotlib import pyplot as plt
import numpy as np

import math

import pandas as pd
from tqdm import tqdm
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

# ===============================
# Eq.(27)
# ===============================
def generate_offsets_eq27(periods):

    n = len(periods)

    H = periods[0]
    G = [1]

    for i in range(1, n):
        G_i = math.gcd(H, periods[i])
        G.append(G_i)
        H = math.lcm(H, periods[i])

    ranges = [[0]] + [range(g) for g in G[1:]]

    return itertools.product(*ranges), G

# =====================================
# Eq.(28)
# C = n * ∏_{i=2}^n T_i
# =====================================
def compute_complexity_eq28(periods):

    n = len(periods)

    prod = 1
    for i in range(1, n):
        prod *= periods[i]
        # print(f"Period T{i+1}={periods[i]}, C partial product={prod}")
    return n * prod



def print_offset_ranges(periods):

    import math

    n = len(periods)

    H = periods[0]
    G = []

    for i in range(1, n):
        G_i = math.gcd(H, periods[i])
        G.append(G_i)
        H = math.lcm(H, periods[i])

    print("\n=== Offset Design Space (Eq.27) ===")
    print(f"Periods: {periods}\n")

    print("Offset ranges:")

    # φ1
    print("φ1 ∈ {0}")

    # φ2 ... φn
    for i, g in enumerate(G, start=2):
        print(f"φ{i} ∈ [0, {g-1}]  (G{i}={g})")

    # 空间大小
    space_size = 1
    for g in G:
        space_size *= g

    print(f"\nTotal offset space size: {space_size}")


# ===============================
# chunk工具（关键优化）
# ===============================
def chunked_iterable(iterable, chunk_size):

    chunk = []

    for item in iterable:
        chunk.append(item)
        if len(chunk) == chunk_size:
            yield chunk
            chunk = []

    if chunk:
        yield chunk

def get_chunk_size(space_size):
    num_workers = os.cpu_count()
    base = space_size // (num_workers * 100)
    return int(min(50000, max(10000, base)))

# ===============================
# 并行 worker（批处理版本）
# ===============================
def evaluate_offsets_batch(args):
    periods, offsets_batch, num_tasks = args

    min_latency = float("inf")
    max_latency = -float("inf")

    min_offsets = None
    max_offsets = None

    for offsets in offsets_batch:

        read_offsets = list(offsets)

        _, _, _, stats = run_analysis_zero_let(
            num_tasks,
            periods,
            read_offsets,
            read_offsets,
            0
        )

        latency = stats["max"]

        if latency < min_latency:
            min_latency = latency
            min_offsets = read_offsets

        if latency > max_latency:
            max_latency = latency
            max_offsets = read_offsets

    return min_latency, min_offsets, max_latency, max_offsets


# ===============================
# 单次实验（高性能版）
# ===============================
def run_single_experiment(num_chains, period_choices,seed):
    trial = 0
    while True:
        periods = random.choices(period_choices, k=num_chains)
        offset_space, G = generate_offsets_eq27(periods)
        C = compute_complexity_eq28(periods)

        space_size = 1
        for g in G[1:]:
            space_size *= g

        if C <= 1e9 and space_size <= 1e5:
            break

        trial += 1
        if trial > 1000:
            p_choices = [1, 2, 5, 10, 20, 50]
            periods = random.choices(p_choices, k=num_chains)

    # periods = [15,10,12]
    print_offset_ranges(periods)

    min_latency = float("inf")
    max_latency = -float("inf")

    min_offsets = None
    max_offsets = None

    chunk_size = get_chunk_size(space_size)
    num_chunks = (space_size + chunk_size - 1) // chunk_size

    tasks = (
        (periods, chunk, num_chains)
        for chunk in chunked_iterable(offset_space, chunk_size)
    )
    start_time = time.perf_counter()

    with Pool(cpu_count()) as p:

        for min_l, min_o, max_l, max_o in tqdm(
            p.imap_unordered(evaluate_offsets_batch, tasks),
            total=num_chunks,
            desc=f"n={num_chains}",
            unit="chunk"
        ):

            if min_l < min_latency:
                min_latency = min_l
                min_offsets = min_o

            if max_l > max_latency:
                max_latency = max_l
                max_offsets = max_o

    R = time.perf_counter() - start_time

    print(f"Experiment completed for n={num_chains}: C={C}, R={R:.6f} seconds, R/C={R/C:.6e}, "f"Min Latency={min_latency} (Offsets: {min_offsets}), Max Latency={max_latency} (Offsets: {max_offsets})")
    return {
        "n": num_chains,
        "periods": periods,
        "seed": seed,
        "C": C,
        "R": R,
        "R_over_C": R / C if C > 0 else None,
        "min_latency": min_latency,
        "min_offsets": min_offsets,
        "max_latency": max_latency,
        "max_offsets": max_offsets
    }


def run_evaluation_zero_let(num_limit, num_chains, num_repeats, period_choices, random_seed):
    TOLERANCE = 1e-9
    all_results = []

    for i in range(num_repeats):
        random.seed(random_seed)
        for n in range(num_limit, num_chains + 1):
            print(f"Running experiment for n={n}, repeat {i+1}/{num_repeats}...")
            result = run_single_experiment(n, period_choices, random_seed)
            all_results.append(result)
        random_seed = random_seed + 1
    return all_results



def output_zero_let(timestamp, num_chains, num_repeats, random_seed, results):
    folder_path = "data"
    os.makedirs(folder_path, exist_ok=True)

    filename = f"data_zero_let_RC_n{num_chains}_{num_repeats}_{random_seed}_{timestamp}.csv"
    results_csv = os.path.join(folder_path, filename)

    with open(results_csv, mode="w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([
            "n",
            "periods",
            "seed",
            "C",
            "R",
            "R/C",
            "min_latency (LZ-)",
            "min_offsets",
            "max_latency (LZ+)",
            "max_offsets"
        ])

        for r in results:
            writer.writerow([
                r["n"],
                r["periods"],
                r["seed"],
                r["C"],
                f"{r['R']:.6f}",
                f"{r['R_over_C']:.6e}" if r["R_over_C"] else "",
                r["min_latency"],
                r["min_offsets"],
                r["max_latency"],
                r["max_offsets"]
            ])
    return results_csv

def plot_R_over_C_from_csv(csvfile, num_chains, num_repeats, random_seed, timestamp):
    folder_path = "data"
    os.makedirs(folder_path, exist_ok=True)
    plot_name = os.path.join(folder_path, f"zero_let_RC_n{num_chains}_{num_repeats}_{random_seed}_{timestamp}.png")

    df = pd.read_csv(csvfile)

    plt.figure()

    markers = ['o', 's', '^', 'D', 'v', 'P', '*', 'X']
    colors = plt.cm.tab10.colors

    for i, n in enumerate(sorted(df["n"].unique())):
        sub_df = df[df["n"] == n]
        plt.scatter(
            sub_df["C"],
            sub_df["R/C"],
            label=f"n={n}",
            marker=markers[i % len(markers)],
            color=colors[i % len(colors)]
        )

    plt.xscale("log")
    plt.yscale("log")


    plt.xlabel("Complexity (C)")
    plt.ylabel("R / C")
    plt.title("Normalized Runtime (R/C)")

    plt.legend(
        title="Task chain length",
        loc="best",
        fontsize=10
    )
    plt.grid()
    plt.savefig(plot_name)
    plt.show()


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

            start_time = time.perf_counter()

            histogram, latency_list, H, stats = run_analysis_zero_let(
                    num_chains, selected_periods, selected_read_offsets, selected_write_offsets, 0
                )
            end_time = time.perf_counter()
            R = end_time - start_time

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

        # header = [
        #     "$T_i$ period", 
        #     "$L_\mathcal{Z}^-$ minimum offset-free reaction time", 
        #     "$\phase{\zeta_i} of L_\mathcal{Z}^-$ offset of minimum (One of offsets can be obtained the minimum values)", 
        #     "$L_\mathcal{Z}^+$ maximum offset-free reaction time", 
        #     "$\phase{\zeta_i} of L_\mathcal{Z}^+$ offset of maximum (One of offsets can be obtained the maximum values)", 
        #     "$L_\mathcal{Z}^+ - L_\mathcal{Z}^-$ different between maximum and minimum",
        #     "is max-harmonic"
        # ]
        header = [
            "period", 
            "minimum offset-free reaction time", 
            "offset of minimum (One of offsets can be obtained the minimum values)", 
            "maximum offset-free reaction time", 
            "offset of maximum (One of offsets can be obtained the maximum values)", 
            "between maximum and minimum",
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

    # perioddown = 2
    # periodup =12
    
    num_limit = 3
    num_chains = 6
    num_repeats = 100 

    period_choices = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]

    # random_seed = 1755016037  # fixed seed
    # timestamp = datetime.datetime.fromtimestamp(int(time.time())).strftime("%Y%m%d_%H%M%S")

    random_seed = int(time.time())
    timestamp = datetime.datetime.fromtimestamp(random_seed).strftime("%Y%m%d_%H%M%S")

    # results = run_evaluation_and_track_extremes(num_chains, random_seed, perioddown, periodup)
    # output_zero_let_min_max_extremes(timestamp, results, num_chains, perioddown, periodup)    

    results =  run_evaluation_zero_let(num_limit, num_chains, num_repeats, period_choices, random_seed)
    csvfile =  output_zero_let(timestamp, num_chains, num_repeats, random_seed, results)

    # csvfile = "data/data_zero_let_RC_n7_1_1777823022_20260503_234342.csv"  # Example CSV file path
    plot_R_over_C_from_csv(csvfile, num_chains, num_repeats, random_seed, timestamp)


