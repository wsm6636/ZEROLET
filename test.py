#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import datetime
import random
import time
import os
import math

from multiprocessing import Pool, cpu_count
from tqdm import tqdm

from analysis_zero_let import run_analysis_zero_let


# ===============================
# Eq.(27) → 只计算 G
# ===============================
def compute_G(periods):
    H = periods[0]
    G = []

    for i in range(1, len(periods)):
        g = math.gcd(H, periods[i])
        G.append(g)
        H = math.lcm(H, periods[i])

    return G


# ===============================
# index → offset（修复版，正确顺序）
# ===============================
def index_to_offset(idx, G):
    offsets = [0]

    for g in G:
        offsets.append(idx % g)
        idx //= g

    return offsets


# ===============================
# Eq.(28)
# ===============================
def compute_complexity_eq28(periods):
    n = len(periods)
    prod = 1
    for i in range(1, n):
        prod *= periods[i]
    return n * prod


# ===============================
# 打印 offset 空间
# ===============================
def print_offset_ranges(periods, G):

    print("\n=== Offset Design Space (Eq.27) ===")
    print(f"Periods: {periods}\n")

    print("Offset ranges:")

    print("φ1 ∈ {0}")

    for i, g in enumerate(G, start=2):
        print(f"φ{i} ∈ [0, {g-1}]  (G{i}={g})")

    space_size = 1
    for g in G:
        space_size *= g

    print(f"\nTotal offset space size: {space_size}")

    return space_size


# ===============================
# chunk size
# ===============================
def get_chunk_size(space_size):
    num_workers = cpu_count()
    base = space_size // (num_workers * 100)
    return int(min(50000, max(10000, base)))


# ===============================
# worker（区间版本）
# ===============================
def evaluate_range(args):
    periods, G, start, end, num_tasks = args

    min_latency = float("inf")
    max_latency = -float("inf")

    min_offsets = None
    max_offsets = None

    for idx in range(start, end):

        offsets = index_to_offset(idx, G)

        _, _, _, stats = run_analysis_zero_let(
            num_tasks,
            periods,
            offsets,
            offsets,
            0
        )

        latency = stats["max"]

        if latency < min_latency:
            min_latency = latency
            min_offsets = offsets

        if latency > max_latency:
            max_latency = latency
            max_offsets = offsets

    return min_latency, min_offsets, max_latency, max_offsets


# ===============================
# 单次实验（纯枚举）
# ===============================
def run_single_experiment(num_chains, period_choices):

    periods = random.choices(period_choices, k=num_chains)

    G = compute_G(periods)

    space_size = print_offset_ranges(periods, G)

    C = compute_complexity_eq28(periods)

    chunk_size = get_chunk_size(space_size)
    num_chunks = (space_size + chunk_size - 1) // chunk_size

    print(f"chunk_size: {chunk_size}, num_chunks: {num_chunks}")

    tasks = (
        (periods, G, i, min(i + chunk_size, space_size), num_chains)
        for i in range(0, space_size, chunk_size)
    )

    min_latency = float("inf")
    max_latency = -float("inf")

    start_time = time.perf_counter()

    with Pool(cpu_count()) as p:

        for min_l, min_o, max_l, max_o in tqdm(
            p.imap_unordered(evaluate_range, tasks),
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

    print(
        f"\nExperiment completed:"
        f"\nC = {C}"
        f"\nR = {R:.6f} s"
        f"\nR/C = {R/C:.6e}"
        f"\nMin Latency = {min_latency} @ {min_offsets}"
        f"\nMax Latency = {max_latency} @ {max_offsets}"
    )

    return {
        "n": num_chains,
        "periods": periods,
        "C": C,
        "R": R,
        "R_over_C": R / C if C > 0 else None,
        "min_latency": min_latency,
        "min_offsets": min_offsets,
        "max_latency": max_latency,
        "max_offsets": max_offsets
    }


# ===============================
# CSV 输出
# ===============================
def output_csv(result, timestamp):

    os.makedirs("data", exist_ok=True)

    filename = f"data/result_{timestamp}.csv"

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([
            "n", "periods", "C", "R", "R/C",
            "min_latency", "min_offsets",
            "max_latency", "max_offsets"
        ])

        writer.writerow([
            result["n"],
            result["periods"],
            result["C"],
            f"{result['R']:.6f}",
            f"{result['R_over_C']:.6e}",
            result["min_latency"],
            result["min_offsets"],
            result["max_latency"],
            result["max_offsets"]
        ])

    print(f"Saved to {filename}")


# ===============================
# main
# ===============================
if __name__ == "__main__":

    num_chains = 10
    period_choices = [1, 2, 5, 10, 20, 50, 100]

    random.seed(1755016037)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    result = run_single_experiment(num_chains, period_choices)

    # output_csv(result, timestamp)