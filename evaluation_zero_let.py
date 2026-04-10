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
import random
import time
import os
import numpy as np

import math



from analysis_zero_let import run_analysis_zero_let
from evaluation_zero_jitter_order import  generate_period_combinations

def output_zero_let_fixp (random_seed, timestamp, results, num_chains, periods):
    folder_path = "zero_let"
    os.makedirs(folder_path, exist_ok=True)

    results_csv = os.path.join(folder_path, f"data_zero_let_n{num_chains}_{periods}_{random_seed}_{timestamp}.csv" )

    # save results to csv
    with open(results_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["periods","seeds", "read_offsets","write_offsets","min","max","mean","std","diff","(latency, count)" ])

        for ( seed, selected_read_offsets, selected_write_offsets, stats, histogram) in results:
            pairs = [(item["latency"], item["count"]) for item in histogram]
            diff = sum(periods) - stats["max"]
            writer.writerow([periods,seed,selected_read_offsets, selected_write_offsets,stats["min"],stats["max"],stats["mean"],stats["std"],diff,pairs])

    print(f"All results saved to {results_csv}")

    return results_csv



def output_zero_let_all (random_seed, timestamp, results, num_chains, perioddown, periodup):
    folder_path = "zero_let"
    os.makedirs(folder_path, exist_ok=True)

    results_csv = os.path.join(folder_path, f"data_zero_let_n{num_chains}_{perioddown}_{periodup}_{random_seed}_{timestamp}.csv" )

    # save results to csv
    with open(results_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["periods","seeds", "read_offsets","write_offsets","min","max","mean","std","diff","(latency, count)" ])

        for ( seed, periods, selected_read_offsets, selected_write_offsets, stats, histogram) in results:
                pairs = [(item["latency"], item["count"]) for item in histogram]
                diff = sum(periods) - stats["max"]
                writer.writerow([periods,seed,selected_read_offsets, selected_write_offsets,stats["min"],stats["max"],stats["mean"],stats["std"],diff,pairs])

    print(f"All results saved to {results_csv}")

    return results_csv




def output_zero_let_max_per_period(random_seed, timestamp, results, num_chains, perioddown, periodup):
    """
    遍历所有结果，针对每种唯一的 periods 组合，只保留 stats['max'] 最大的那一条记录。
    保存到新的 CSV 文件中。
    """
    folder_path = "zero_let"
    os.makedirs(folder_path, exist_ok=True)

    # 新文件名，添加 _max_only 标记
    results_csv = os.path.join(folder_path, f"data_zero_let_n{num_chains}_{perioddown}_{periodup}_{random_seed}_{timestamp}_MAX_ONLY.csv")

    # 1. 过滤逻辑：字典存储，key 为 periods 的元组，value 为整条记录
    max_results_map = {}

    print("Filtering results: keeping only the max latency case for each period combination...")
    
    for item in results:
        # 解包数据 (根据 run_evaluation_zero_let_all 的返回格式)
        # (seed, periods, read_offsets, write_offsets, stats, histogram)
        seed, periods, r_offsets, w_offsets, stats, histogram = item
        
        # 将 periods 列表转换为元组以便作为字典键
        p_key = tuple(periods)
        current_max = stats["max"]

        if p_key not in max_results_map:
            max_results_map[p_key] = item
        else:
            existing_max = max_results_map[p_key][4]["max"] # 索引4是stats
            if current_max > existing_max:
                max_results_map[p_key] = item

    # 2. 写入文件
    filtered_count = len(max_results_map)
    print(f"Filtered from {len(results)} total records to {filtered_count} records (one per period combination).")
    print(f"Saving max-only results to {results_csv}...")

    with open(results_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        # 表头保持一致
        writer.writerow(["periods", "seeds", "read_offsets", "write_offsets", "min", "max", "mean", "std", "diff", "(latency, count)"])

        # 按 periods 排序输出，方便查看
        sorted_keys = sorted(max_results_map.keys())
        
        for p_key in sorted_keys:
            seed, periods, r_offsets, w_offsets, stats, histogram = max_results_map[p_key]
            
            pairs = [(item["latency"], item["count"]) for item in histogram]
            diff = sum(periods) - stats["max"]
            
            writer.writerow([
                periods, 
                seed, 
                r_offsets, 
                w_offsets, 
                stats["min"], 
                stats["max"], 
                stats["mean"], 
                stats["std"], 
                diff, 
                pairs
            ])

    print(f"Max-only results successfully saved to {results_csv}")
    return results_csv




def compute_effective_offset_limit(periods, index):
    if index == 0:
        return 1  
    
    current_lcm = periods[0]
    for p in periods[1:index]:
        current_lcm = math.lcm(current_lcm, p)
    
    limit = math.gcd(current_lcm, periods[index])
    
    return max(1, limit)


def generate_all_read_combinations(periods):

    if not periods:
        return [()]
    
    ranges = []
    for i, P in enumerate(periods):
        limit = compute_effective_offset_limit(periods, i)

        ranges.append(range(limit))
    
    return list(itertools.product(*ranges))



def generate_all_read_combinations_zero(periods):
    if not periods:
        return [()]
    
    ranges = []
    
    ranges.append([0])
    
    for P in periods[1:]:
        ranges.append(range(P+1))
    
    return list(itertools.product(*ranges))


def generate_all_read_combinations(periods):

    return list(itertools.product(*[range(P) for P in periods]))


def run_evaluation_zero_let_fixp_zero( num_chains, random_seed, periods):
    TOLERANCE = 1e-9
    # preparing list for storing result
    results =[] 

    random.seed(random_seed)
    
    # all_read_combinations = generate_all_read_combinations(periods)
    all_read_combinations = generate_all_read_combinations_zero(periods)

    total = len(all_read_combinations)

    for idx, read_offsets_tuple in enumerate(all_read_combinations):
        selected_periods = periods
        selected_read_offsets = list(read_offsets_tuple)
        selected_write_offsets = selected_read_offsets
        print(f"================== Combination {idx+1}/{total}: periods {selected_periods}, read_offsets {selected_read_offsets}, write_offsets {selected_write_offsets}, random_seed {random_seed} ==================")
        histogram, latency_list, H, stats = run_analysis_zero_let(num_chains, selected_periods,selected_read_offsets,selected_write_offsets, 0)

        results.append((random_seed, selected_read_offsets, selected_write_offsets, stats,  histogram))

        random_seed = random_seed+1
    return results



def run_evaluation_zero_let_fixp( num_chains, random_seed, periods):
    TOLERANCE = 1e-9
    # preparing list for storing result
    results =[] 

    random.seed(random_seed)
    
    all_read_combinations = generate_all_read_combinations(periods)
    # all_read_combinations = generate_all_read_combinations_zero(periods)

    total = len(all_read_combinations)

    for idx, read_offsets_tuple in enumerate(all_read_combinations):
        selected_periods = periods
        selected_read_offsets = list(read_offsets_tuple)
        selected_write_offsets = selected_read_offsets
        print(f"================== Combination {idx+1}/{total}: periods {selected_periods}, read_offsets {selected_read_offsets}, write_offsets {selected_write_offsets}, random_seed {random_seed} ==================")
        histogram, latency_list, H, stats = run_analysis_zero_let(num_chains, selected_periods,selected_read_offsets,selected_write_offsets, 0)

        results.append((random_seed, selected_read_offsets, selected_write_offsets, stats,  histogram))

        random_seed = random_seed+1
    return results




def run_evaluation_zero_let_fixp_write( num_chains, random_seed, periods):
    TOLERANCE = 1e-9
    # preparing list for storing result
    results =[] 

    random.seed(random_seed)
    
    all_read_combinations = generate_all_read_combinations(periods)
    # all_read_combinations = generate_all_read_combinations_zero(periods)
    all_write_combinations = generate_all_read_combinations(periods)

    total = len(all_read_combinations)
    total_w = len(all_write_combinations)

    for idx, read_offsets_tuple in enumerate(all_read_combinations):
        for w_idx, write_offsets_tuple in enumerate(all_write_combinations):
            selected_periods = periods
            selected_read_offsets = list(read_offsets_tuple)
            selected_write_offsets = list(write_offsets_tuple)
            print(f"================== Combination {idx+1}/{total}: periods {selected_periods}, read_offsets {selected_read_offsets}, write_offsets {selected_write_offsets}, random_seed {random_seed} ==================")
            histogram, latency_list, H, stats = run_analysis_zero_let(num_chains, selected_periods,selected_read_offsets,selected_write_offsets, 0)

            results.append((random_seed, selected_read_offsets, selected_write_offsets, stats,  histogram))

            random_seed = random_seed+1
    return results


def run_evaluation_zero_let_all( num_chains, random_seed, perioddown, periodup):
    TOLERANCE = 1e-9
    # preparing list for storing result
    results = []
    all_period_combinations = generate_period_combinations(perioddown, periodup,num_chains)

    random.seed(random_seed)
    for period_combo in all_period_combinations:
        
        # all_read_combinations = generate_all_read_combinations(period_combo)
        all_read_combinations = generate_all_read_combinations_zero(period_combo)
        total = len(all_read_combinations)
        
        for idx, (read_offsets_tuple) in enumerate(all_read_combinations):
            selected_periods = list(period_combo)
            selected_read_offsets = list(read_offsets_tuple)
            selected_write_offsets = selected_read_offsets

            print(f"================== Combination {idx+1}/{total}: periods {selected_periods}, read_offsets {selected_read_offsets}, write_offsets {selected_write_offsets}, random_seed {random_seed} ==================")
            histogram, latency_list, H, stats = run_analysis_zero_let(num_chains, selected_periods,selected_read_offsets,selected_write_offsets, 0)

            results.append((random_seed,selected_periods, selected_read_offsets, selected_write_offsets, stats, histogram))

    random_seed = random_seed+1
    return results


def run_evaluation_and_track_extremes(num_chains, random_seed, perioddown, periodup):
    all_period_combinations = generate_period_combinations(perioddown, periodup, num_chains)
    random.seed(random_seed)
    
    # 数据结构：{ (p1, p2, p3): { 'min_record': {...}, 'max_record': {...} } }
    period_stats_map = {}
    
    total_combos = len(all_period_combinations)
    
    print(f"Starting evaluation for {total_combos} period combinations...")

    for p_idx, period_combo in enumerate(all_period_combinations):
        p_key = tuple(period_combo)
        
        # 初始化该周期的记录容器
        if p_key not in period_stats_map:
            period_stats_map[p_key] = {
                'min_record': None, # 记录 stats['max'] 最小的情况
                'max_record': None  # 记录 stats['max'] 最大的情况
            }
        
        all_read_combinations = generate_all_read_combinations_zero(period_combo)
        total_offsets = len(all_read_combinations)
        
        # 进度提示 (每处理完一个周期组合打印一次)
        print(f"[{p_idx+1}/{total_combos}] Processing Periods: {period_combo} ({total_offsets} offset combos)...")

        current_seed = random_seed + p_idx # 简单处理seed，或者根据你的逻辑调整
        
        for idx, read_offsets_tuple in enumerate(all_read_combinations):
            selected_periods = list(period_combo)
            selected_read_offsets = list(read_offsets_tuple)
            selected_write_offsets = selected_read_offsets # 根据你的逻辑，write = read

            # 执行核心分析
            # 注意：这里假设 run_analysis_zero_let 返回 (histogram, latency_list, H, stats)
            try:
                histogram, latency_list, H, stats = run_analysis_zero_let(
                    num_chains, selected_periods, selected_read_offsets, selected_write_offsets, 0
                )
            except Exception as e:
                print(f"Error processing {selected_periods} with offsets {selected_read_offsets}: {e}")
                continue

            current_max_latency = stats["max"]
            
            # 构造当前运行的完整记录对象，方便后续提取
            current_record = {
                "seed": current_seed + idx,
                "periods": selected_periods,
                "read_offsets": selected_read_offsets,
                "write_offsets": selected_write_offsets,
                "stats": stats,
                "histogram": histogram,
                "diff": sum(selected_periods) - current_max_latency
            }

            # --- 更新最小值记录 ---
            min_rec = period_stats_map[p_key]['min_record']
            if min_rec is None or current_max_latency < min_rec["stats"]["max"]:
                period_stats_map[p_key]['min_record'] = current_record

            # --- 更新最大值记录 ---
            max_rec = period_stats_map[p_key]['max_record']
            if max_rec is None or current_max_latency > max_rec["stats"]["max"]:
                period_stats_map[p_key]['max_record'] = current_record

    return period_stats_map

def output_zero_let_min_max_extremes(timestamp, period_stats_map, num_chains, perioddown, periodup):
    folder_path = "zero_let"
    os.makedirs(folder_path, exist_ok=True)

    filename = f"data_zero_let_n{num_chains}_{perioddown}_{periodup}_EXTREMES_{timestamp}.csv"
    results_csv = os.path.join(folder_path, filename)

    print(f"Writing extreme values to {results_csv}...")

    with open(results_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        
        # 定义表头
        header = [
            "period", 
            "min", "readoffset_min", "writeoffset_min", "diff_min",
            "max", "readoffset_max", "writeoffset_max", "diff_max"
        ]
        writer.writerow(header)

        # 按周期排序输出
        sorted_keys = sorted(period_stats_map.keys())

        for p_key in sorted_keys:
            data = period_stats_map[p_key]
            min_rec = data['min_record']
            max_rec = data['max_record']

            if not min_rec or not max_rec:
                continue

            # 提取最小值相关数据
            p_str = str(min_rec["periods"])
            val_min_max = min_rec["stats"]["max"]
            ro_min = str(min_rec["read_offsets"])
            wo_min = str(min_rec["write_offsets"])
            diff_min = min_rec["diff"]

            # 提取最大值相关数据
            val_max_max = max_rec["stats"]["max"]
            ro_max = str(max_rec["read_offsets"])
            wo_max = str(max_rec["write_offsets"])
            diff_max = max_rec["diff"]

            writer.writerow([
                p_str,
                val_min_max, ro_min, wo_min, diff_min,
                val_max_max, ro_max, wo_max, diff_max
            ])

    print(f"Extreme values successfully saved to {results_csv}")
    return results_csv




if __name__ == "__main__":

    periods = [12,8,9]

    perioddown = 2
    periodup =12

    num_chains = 3 
    
    random_seed = 1755016037  # fixed seed
    timestamp = datetime.datetime.fromtimestamp(int(time.time())).strftime("%Y%m%d_%H%M%S")

    # random_seed = int(time.time())
    # timestamp = datetime.datetime.fromtimestamp(random_seed).strftime("%Y%m%d_%H%M%S")
    
    # results = run_evaluation_zero_let_fixp_zero( num_chains,  random_seed, periods)
    # output_zero_let_fixp(random_seed, timestamp, results, num_chains, periods)

    # results = run_evaluation_zero_let_all( num_chains,  random_seed, perioddown, periodup)
    # output_zero_let_all(random_seed, timestamp, results, num_chains, perioddown, periodup)
    # output_zero_let_max_per_period(random_seed, timestamp, results, num_chains, perioddown, periodup)

    # results = run_evaluation_and_track_extremes(num_chains, random_seed, perioddown, periodup)
    # output_zero_let_min_max_extremes(timestamp, results, num_chains, perioddown, periodup)    

    # results = run_evaluation_zero_let_fixp_write( num_chains,  random_seed, periods)
    # output_zero_let_fixp(random_seed, timestamp, results, num_chains, periods)

    results = run_evaluation_zero_let_fixp( num_chains,  random_seed, periods)
    output_zero_let_fixp(random_seed, timestamp, results, num_chains, periods)

