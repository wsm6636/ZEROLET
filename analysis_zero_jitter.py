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
import random
from scipy.optimize import basinhopping
from analysis_passive import  Event, Task, RandomEvent
from analysis_passive import euclide_extend
from evaluation_passive import generate_periods_and_offsets

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


def chain_asc_zero_jitter(tasks):
    """
    Processing Chain without adjustment of offset
    In ascending order of the task's index in the chain
    arguments:
        tasks: the task set in the chain
    return: 
        (r, w): the combined read and write events of the chain
        False: if the events do not conform to the theorems
    """
    n = len(tasks)
    # Start from the head of the chain and combine backwards
    current_task = tasks[0]

    for i in range(1, n):
        result = combine_zero_jitter(current_task, tasks[i])
        if result is False:
            return False
        else:
            r, w, max_latency = result
            current_task = Task(read_event=r, write_event=w, id=r.id)
    return  r, w, max_latency


def our_chain_zero_jitter(tasks):
    if len(tasks) == 1:
        # Our analysis is also valid for a task
        final_r = tasks[0].read_event
        final_w = tasks[0].write_event
        max_latency = final_w.offset - final_r.offset
        return max_latency, final_r, final_w
    else:
        final_combine_result = chain_asc_zero_jitter(tasks)
        if final_combine_result:
            final_r, final_w, max_latency = final_combine_result
            # max reaction time need to add the period of the first read event
            return max_latency, final_r, final_w
        else:
            return False


results_function = []


# outport function
def run_analysis_zero_jitter(num_tasks, periods,read_offsets,write_offsets, per_jitter):
    global results_function
    results_function = []  

    tasks = RandomEvent(num_tasks, periods,read_offsets,write_offsets, per_jitter).tasks

    final = our_chain_zero_jitter(tasks)
    
    if final is False:
        best_latency = 0
        final_r = None
        final_w = None
    else:
        best_latency = final[0]
        final_r = final[1]
        final_w = final[2]

    return best_latency, final_r, final_w



# test the code
if __name__ == "__main__":
    num_tasks = 100
    periods = [1, 2, 5, 10, 20, 50, 100, 200, 1000]
    
    per_jitter = 0 # percent jitter

    selected_periods = random.choices(periods,  k=num_tasks)
    selected_read_offsets = [random.randint(0, period) for period in selected_periods]
    selected_write_offsets = [read_offset + period for read_offset, period in zip(selected_read_offsets, selected_periods)]

    print(selected_periods)
    print(selected_read_offsets)
    print(selected_write_offsets)

    tasks = RandomEvent(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter).tasks

    final = our_chain_zero_jitter(tasks)
    
    if final is False:
        print("No valid merge order found.")
    else:
        best_latency = final[0]
        final_r = final[1]
        final_w = final[2]

    
    print(best_latency)
    print("Final read event:", final_r)
    print("Final write event:", final_w)



