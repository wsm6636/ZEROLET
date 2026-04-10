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

import math
from functools import reduce
from collections import defaultdict

from tqdm import tqdm 
from analysis_passive import RandomEvent


def lcm(a, b):
    return abs(a * b) // math.gcd(a, b)


def lcm_list(numbers):
    return reduce(lcm, numbers, 1)

def compute_latency_stats(histogram, total_count):
    """
    Compute min, max, mean, std from histogram
    histogram: [{"latency": x, "count": c}, ...]
    total_count: hyperperiod
    """

    if total_count == 0:
        return None

    latencies = [item["latency"] for item in histogram]

    min_latency = latencies[0]
    max_latency = latencies[-1]

    # mean
    mean = sum(item["latency"] * item["count"] for item in histogram) / total_count

    # std
    variance = sum(
        item["count"] * (item["latency"] - mean) ** 2
        for item in histogram
    ) / total_count

    std = math.sqrt(variance)

    return {
        "min": round(min_latency, 3),
        "max": round(max_latency, 3),
        "mean": round(mean, 3),
        "std": round(std, 3)
    }


def compute_chain_latency_from_z(z, tasks):

    current_time = z

    for task in tasks:

        T = task.period
        r = task.read_event.offset
        w = task.write_event.offset

        # Find smallest job index k such that read_time >= current_time
        k = math.ceil((current_time - r) / T)

        if k < 0:
            k = 0

        # Compute write time of this job
        write_time = k * T + w

        # Update current time for next task
        current_time = write_time

    latency = current_time - z

    return latency

def compute_latency_histogram(tasks):

    periods = [task.period for task in tasks]
    H = lcm_list(periods)

    histogram_dict = defaultdict(int)
    latency_list = []
    offsets = [task.read_event.offset for task in tasks]
    max_offset = max(offsets)

    # for z in range(H):
    for z in range(max_offset, H+max_offset):

        latency = compute_chain_latency_from_z(z, tasks)
        latency = round(latency, 9)

        histogram_dict[latency] += 1
        latency_list.append(latency)

    # convert to sorted histogram list of dict
    histogram_result = [
        {"latency": latency, "count": histogram_dict[latency]}
        for latency in sorted(histogram_dict)
    ]

    return histogram_result, latency_list, H


def run_analysis_zero_let(num_tasks, periods,read_offsets,write_offsets, per_jitter):
    tasks = RandomEvent(num_tasks, periods,read_offsets,write_offsets, per_jitter).tasks

    histogram, latency_list, H = compute_latency_histogram(tasks)
    stats = compute_latency_stats(histogram, H)


    return  histogram, latency_list, H, stats


if __name__ == "__main__":

    # Example from your case
    periods = [15,10,12]
    read_offsets = [11,18,26]
    write_offsets = read_offsets
    # write_offsets = [4,3,8]

    tasks = []
    tasks = RandomEvent(len(periods), periods, read_offsets, write_offsets, 0).tasks

    histogram, latency_list, H = compute_latency_histogram(tasks)

    # print("Hyperperiod:", H)
    # print()

    # print("z -> latency")
    # for z, latency in enumerate(latency_list):
    #     print(f"{z:2d} -> {latency}")

    # print("\nHistogram:")
    # for item in histogram:
    #     print(f"Latency: {item['latency']:.6f}, Count: {item['count']}")
    print(f"Hyperperiod: {H}")
    # print(f"Latency histogram: {histogram}")
    # print(f"Latency list: {latency_list}")
    print(f"Latency stats: {compute_latency_stats(histogram, H)}")
