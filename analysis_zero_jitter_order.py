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
from functools import reduce
import math
import random
from scipy.optimize import basinhopping
from analysis_passive import  Event, Task, RandomEvent
from analysis_passive import euclide_extend
from evaluation_passive import generate_periods_and_offsets
from analysis_zero_jitter import our_chain_zero_jitter

def combine_zero_jitter(task1 ,task2):
    rd_ph1 = task1.read_event.offset
    wr_ph1 = task1.write_event.offset
    T1 = task1.write_event.period

    rd_ph2 = task2.read_event.offset
    wr_ph2 = task2.write_event.offset
    T2 = task2.read_event.period


    # distance from tau_1 job 0 write  -->  tau_2 job 0 read
    PPhase = rd_ph2-wr_ph1

    # G = GCD(T1,T2)
    # c1, c2 are coefficients of Bezout's identity: c1*T1+c2*T2 = G
    (G,c1,c2) = euclide_extend(T1,T2)
    p1 = T1//G
    p2 = T2//G

    # Minimum latency
    min_latency = (wr_ph1-rd_ph1)+(wr_ph2-rd_ph2)+(PPhase % G)

    # Parameters of the 1 -> 2 chain
    if T1 == T2:
    # assuming jobs of the chain 1->2 are indexed by T1
        T12 = T1
        rd_ph12 = rd_ph1
        rd_delta12 = wr_delta12 = T1
        cycle = 1
        wr_ph12 = wr_ph2-PPhase+(PPhase % T1)
        max_latency = min_latency
        id_min_latency = 0
        id_max_latency = 0

        r_1_2_offset = rd_ph12
        w_1_2_offset = wr_ph12

    elif T1 > T2:
        T12 = T1
        phi1 = (PPhase % T2) // G      # Eq. (23)
        rd_ph12 = rd_ph1
        rd_delta12 = T1                # constant separation of consecutive reads
        dancing = [(phi1-j1*p1) % p2 for j1 in range(p2)]  # the job-dependent piece of (22)
        cycle = p2
        # Write phasing, Eq. (24)
        wr_ph12 = [wr_ph2-PPhase+rem*G+(PPhase % G) for rem in dancing]
        # separation of consecutive writes
        wr_delta12 = [(p1//p2)*T2 if (rem >= p1 % p2) else (p1//p2+1)*T2 for rem in dancing]
        inv_p1 = c1 % p2   # multiplicative inverse of p1 over modulo-p2
        # Notice that min/max below are computed without enumerating dancing
        max_latency = min_latency+T2-G
        id_min_latency = (phi1*inv_p1) % p2      # same id as min in dancing
        id_max_latency = ((phi1+1)*inv_p1) % p2  # same id as max in dancing
        # Read phase of the copier task after tau_2. Eq. (37)
        rd_ph2next = wr_ph2-PPhase+(PPhase % G)+T2-G

        r_1_2_offset = rd_ph12
        w_1_2_offset = wr_ph12[id_max_latency]

    else:
        T12 = T2
        phi2 = (PPhase % T1) // G      # Eq. (32)
        wr_ph12 = wr_ph2
        wr_delta12 = T2                # constant separation of consecutive writes
        dancing = [(phi2+j2*p2) % p1 for j2 in range(p1)]  # the job-dependent piece of (31)
        cycle = p1
        # Read phasing, Eq. (33)
        rd_ph12 = [rd_ph1+PPhase-(PPhase % G)-rem*G for rem in dancing]
        # separation of consecutive reads
        rd_delta12 = [(p2//p1+1)*T1 if (rem >= (-p2) % p1) else (p2//p1)*T1 for rem in dancing]
        inv_p2 = c2 % p1   # multiplicative inverse of p2 over modulo-p1
        # Notice that min/max below are computed without enumerating dancing
        max_latency = min_latency+T1-G
        id_min_latency = (-phi2*inv_p2) % p1     # same id as max in dancing
        id_max_latency = (-(phi2+1)*inv_p2) % p1 # same id as min in dancing
        # Write phase of the copier task before tau_1. Eq. (40)
        wr_ph1prev = rd_ph1+PPhase-(PPhase % G)-T1+G

        r_1_2_offset = rd_ph12[id_max_latency]
        w_1_2_offset = wr_ph12

    combined_id = f"({task1.id}_{task2.id})"
    r_1_2 = Event(
        id=combined_id,
        event_type="read_combined",
        period=T12,
        offset=r_1_2_offset,
        maxjitter=0,
    )  
    w_1_2 = Event(
        id=combined_id,
        event_type="write_combined",
        period=T12,
        offset=w_1_2_offset,
        maxjitter=0,
    )  

    return r_1_2, w_1_2, max_latency 



def our_chain_zero_jitter_order(tasks):
    n = len(tasks)
    if n == 0:
        return []
    if n == 1:
        final_r = tasks[0].read_event
        final_w = tasks[0].write_event
        # max_latency = final_w.offset - final_r.offset + final_r.period
        max_latency = final_w.offset - final_r.offset
        return [(max_latency, tasks[0])]
    
    results = []
    
    # 尝试合并每一对相邻任务
    for i in range(len(tasks) - 1):
        left_task = tasks[i]
        right_task = tasks[i + 1]
        
        # 合并这两个任务
        res = combine_zero_jitter(left_task, right_task)
        if res:
            final_r, final_w, max_latency = res
            merged_task = Task(read_event=final_r, write_event=final_w, id=final_r.id)

            # print(f"Merged tasks {left_task.id} and {right_task.id} into {merged_task.id} with latency {max_latency}")
            # print(f"  Read Event - Period: {final_r.period}, Offset: {final_r.offset}")
            # print(f"  Write Event - Period: {final_w.period}, Offset: {final_w.offset}")
            
            # 创建新的任务列表，用合并后的任务替换原来的两个任务
            new_task_list = tasks[:i] + [merged_task] + tasks[i+2:]
            
            # 递归处理新的任务列表
            sub_results = our_chain_zero_jitter_order(new_task_list)
            results.extend(sub_results)


    return results


def lcm(a, b):
    return abs(a * b) // math.gcd(a, b)

def lcm_list(numbers):
    return reduce(lcm, numbers, 1)

# ----------------------------

def find_chain_jobs_in_hyperperiod(tasks):
    if not tasks:
        return [], [], 0

    periods = [t.period for t in tasks]
    H = lcm_list(periods)
    
    # First task's job count in [0, H)
    T1 = tasks[0].period
    R1 = tasks[0].read_event.offset
    W1 = tasks[0].write_event.offset

    k1_max = H // T1
    
    rd_gamma = []
    wr_gamma = []

    for k1 in range(k1_max):
        current_time = W1 + k1 * T1  # τ1 writes at this time
        
        # Propagate through the chain
        valid = True
        current_k = k1
        for i in range(1, len(tasks)):
            Ti, Ri, Wi = tasks[i].period, tasks[i].read_event.offset, tasks[i].write_event.offset
            # Find smallest ki such that Ri + ki*Ti >= current_time
            if current_time <= Ri:
                ki = 0
            else:
                diff = current_time - Ri
                ki = (diff + Ti - 1) // Ti  # ceil(diff / Ti)
            
            read_time = Ri + ki * Ti
            if read_time < current_time:
                valid = False
                break
            
            current_time = Wi + ki * Ti  # update to write time of τi
        
        if valid:
            rd_start = R1 + k1 * T1
            wr_end = current_time
            rd_gamma.append(rd_start)
            wr_gamma.append(wr_end)
    

    # === Deduplication: for same wr_end, keep MAX rd_start (latest input) ===
    wr_to_best_rd = {}
    for rd, wr in zip(rd_gamma, wr_gamma):
        if wr not in wr_to_best_rd or rd > wr_to_best_rd[wr]:
            wr_to_best_rd[wr] = rd

    # Sort by wr (chronological order)
    sorted_items = sorted(wr_to_best_rd.items())  # (wr, rd)
    wr_gamma = [wr for wr, _ in sorted_items]
    rd_gamma = [rd for _, rd in sorted_items]


    return rd_gamma, wr_gamma, H




def compute_four_latencies(rd_gamma, wr_gamma,p):
    n = len(rd_gamma)
    # print(f"Number of chain jobs found: {n}")
    
    if n == 1:
        D_LF = wr_gamma[0] - rd_gamma[0]
        D_FF = D_LF + p
        D_LL = D_LF + p
        D_FL = D_LF + 2 * p
        return D_LF, D_FF, D_LL, D_FL

    # D^LF = max{ wr_γ(ℓ) - rd_γ(ℓ) }
    D_LF = max(wr_gamma[i] - rd_gamma[i] for i in range(n))
    
    # D^FF = max{ wr_γ(ℓ) - rd_γ(ℓ-1) } for ℓ >= 1
    D_FF = max(wr_gamma[i] - rd_gamma[i-1] for i in range(1, n))
    
    # D^LL = max{ wr_γ(ℓ+1) - rd_γ(ℓ) } for ℓ from 0 to n-2
    D_LL = max(wr_gamma[i+1] - rd_gamma[i] for i in range(n - 1))
    
    # D^FL = max{ wr_γ(ℓ+1) - rd_γ(ℓ-1) } for ℓ from 1 to n-2
    if n >= 3:
        D_FL = max(wr_gamma[i+1] - rd_gamma[i-1] for i in range(1, n - 1))
    else:
        D_FL = D_LL + p
    

    return D_LF, D_FF, D_LL, D_FL


def compute_four_latencies_zero_jitter(best_task):
    latencyLF = best_task.write_event.offset - best_task.read_event.offset
    latencyFF = latencyLF + best_task.period
    latencyLL = latencyLF + best_task.period
    latencyFL = latencyLF + best_task.period * 2

    # print(f"D^LF (Last-to-First) : {latencyLF}")
    # print(f"D^FF (First-to-First) : {latencyFF}")
    # print(f"D^LL (Last-to-Last)  : {latencyLL}")
    # print(f"D^FL (First-to-Last)  : {latencyFL}\n")

    return latencyLF, latencyFF, latencyLL, latencyFL


# outport function
def run_analysis_zero_jitter_order(num_tasks, periods,read_offsets,write_offsets, per_jitter):
    global results_function
    best_result = []  

    tasks = RandomEvent(num_tasks, periods,read_offsets,write_offsets, per_jitter).tasks

    final = our_chain_zero_jitter_order(tasks)
    zerojitter_final = our_chain_zero_jitter(tasks)

    sum_period = sum([t.period for t in tasks])

    if final:
        best_latency, best_task = min(final, key=lambda x: x[0])
        best_merge_pair = best_task.read_event.id
        best_result = [best_latency,best_merge_pair,best_task]
    else : 
        best_result= None


    # Step 1: Group by rounded latency
    latency_stats = defaultdict(lambda: {"count": 0, "ids": []})
    for latency, task in final:
        key = round(latency, 9)
        latency_stats[key]["count"] += 1
        latency_stats[key]["ids"].append(task.id)

    # Step 2: Convert to sorted list of dicts
    count_result = []
    for lat in sorted(latency_stats.keys()):
        stats = latency_stats[lat]
        count_result.append({
            "latency": lat,
            "count": stats["count"],
            "ids": stats["ids"]
        })

    return  zerojitter_final, best_result, count_result, sum_period


def run_analysis_zero_jitter_original(num_tasks, periods,read_offsets,write_offsets, per_jitter):

    tasks = RandomEvent(num_tasks, periods,read_offsets,write_offsets, per_jitter).tasks

    rd_gamma, wr_gamma, H = find_chain_jobs_in_hyperperiod(tasks)

    # print(rd_gamma)
    # print(wr_gamma)
    # print(f"\nHyperperiod H = {H}")
    # print(f"Number of chain jobs = {len(rd_gamma)}")
    # print("\nChain Jobs (i, rd(i), wr(i), latency):")
    # for i, (rd, wr) in enumerate(zip(rd_gamma, wr_gamma)):
    #     print(f"  i={i}: rd={rd}, wr={wr}, delay={wr - rd}")
    
    result = compute_four_latencies(rd_gamma, wr_gamma,periods[0])

    # print(f"D^LF (Last-to-First) : {result[0]}")
    # print(f"D^FF (First-to-First) : {result[1]}")
    # print(f"D^LL (Last-to-Last)  : {result[2]}")
    # print(f"D^FL (First-to-Last)  : {result[3]}")
    
    return result





# test the code
if __name__ == "__main__":
    num_tasks = 3
    
    per_jitter = 0 # percent jitter

    selected_periods = [3,4,6]
    selected_read_offsets = [0,0,1]
    selected_write_offsets = [1,1,2]

    print(selected_periods)
    print(selected_read_offsets)
    print(selected_write_offsets)

    tasks = RandomEvent(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter).tasks

    rd_gamma, wr_gamma, H = find_chain_jobs_in_hyperperiod(tasks)
    
    # print(f"\nHyperperiod H = {H}")
    # print(f"Number of chain jobs = {len(rd_gamma)}")
    # print("\nChain Jobs (i, rd(i), wr(i), latency):")
    # for i, (rd, wr) in enumerate(zip(rd_gamma, wr_gamma)):
    #     print(f"  i={i}: rd={rd}, wr={wr}, delay={wr - rd}")
    
    result = compute_four_latencies(rd_gamma, wr_gamma,selected_periods[0])
    
    print(f"result: original")
    print(f"D^LF (Last-to-First) : {result[0]}")
    print(f"D^FF (First-to-First) : {result[1]}")
    print(f"D^LL (Last-to-Last)  : {result[2]}")
    print(f"D^FL (First-to-Last)  : {result[3]}")

    print("\n=== our ===")
    final = our_chain_zero_jitter_order(tasks)
    zerojitter_final = our_chain_zero_jitter(tasks)
    zerojitter = zerojitter_final[0] if zerojitter_final else None
    zero_jitter_task = Task(read_event=zerojitter_final[1], write_event=zerojitter_final[2], id=zerojitter_final[1].id)

    if final:
        best_latency, best_task = min(final, key=lambda x: x[0])
        best_merge_pair = best_task.read_event.id
        best_result = [best_latency,best_merge_pair,best_task]
    else : 
        best_result= None

    # Step 1: Group by rounded latency
    latency_stats = defaultdict(lambda: {"count": 0, "ids": []})
    for latency, task in final:
        key = round(latency, 9)
        latency_stats[key]["count"] += 1
        latency_stats[key]["ids"].append(task.id)
        # print(f"task id: {task.id}")

    # Step 2: Convert to sorted list of dicts
    count_result = []
    for lat in sorted(latency_stats.keys()):
        stats = latency_stats[lat]
        count_result.append({
            "latency": lat,
            "count": stats["count"],
            "ids": stats["ids"]
        })
    
    print(f"best latency {best_result[0]}, id:{best_result[1]}, zero jitter latency: {zerojitter if zerojitter else 'N/A'}")
    for item in count_result:
        print(f"Latency: {item['latency']:.6f}, Count: {item['count']}")

    best_task = best_result[2]

    print(f"result: best_task")
    compute_four_latencies_zero_jitter(best_task)
    print(f"result: zero_jitter_task")
    compute_four_latencies_zero_jitter(zero_jitter_task)

    print(f"best_merge_pair: {best_merge_pair}")