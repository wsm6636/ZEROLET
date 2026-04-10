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

import sys
from evaluation_passive import generate_periods_and_offsets
from evaluation_passive import generate_LET

from analysis_passive import run_analysis_passive_our
from evaluation_passive import output_passive_our

from analysis_passive import run_analysis_passive_Gunzel_LET
from evaluation_passive import output_passive_Gunzel_LET

from analysis_passive import run_analysis_passive_Gunzel_IC
from evaluation_passive import output_passive_Gunzel_IC

from analysis_active import run_analysis_active_our
from evaluation_active import output_active_our

from analysis_active import run_analysis_active_Gunzel_LET
from evaluation_active import output_active_Gunzel_LET

from analysis_active import run_analysis_active_Gunzel_IC
from evaluation_active import output_active_Gunzel_IC

from analysis_Gunzel import run_analysis_Gunzel_IC
from analysis_Gunzel import run_analysis_Gunzel_LET

# new evaluation
from analysis_active_add import run_analysis_active_our_add
from evaluation_active_add import output_active_our_add

from analysis_passive_order import run_analysis_passive_our_order
from evaluation_passive_order import output_passive_our_order

from analysis_active_add_order import run_analysis_active_our_add_order
from evaluation_active_add_order import output_active_our_add_order

from plot import compare_false_percent_our
from plot import compare_plot_histogram_our

import random
import datetime
import time
import os
import argparse
import pandas as pd


def convert_to_our_offsets(schedule_wcet, task_set, schedule_bcet, new_task_set):
    """
    Extract offset and jitter parameters from the Gunzel schedule that match our paper
    arguments:
        schedule_wcet: WCET (worst-case execution time) schedule
        task_set: task set
        schedule_bcet: BCET (best-case execution time) schedule
        new_task_set: new task set
    return:
        tuple: (read jitter list, write jitter list, read offset list, write offset list)
    """
    selected_read_offsets = []
    selected_write_offsets = []
    read_jitters = []
    write_jitters = []

    # From the same schedule produced by Gunzel IC, 
    # for each task , computed the events and min/max task latencies of Eq. (6), 
    # as described in Section II.B.
    for i, (t_bcet, t_wcet) in enumerate(zip(new_task_set, task_set)):
        seq_bcet = schedule_bcet[t_bcet]
        seq_wcet = schedule_wcet[t_wcet]
        Tb = t_bcet.period
        Tw = t_wcet.period
        tr_bcet = [tr - j*Tb for j, (tr, _) in enumerate(seq_bcet)]
        tw_bcet = [tw - j*Tb for j, (_, tw) in enumerate(seq_bcet)]

        tr_wcet = [tr - j*Tw for j, (tr, _) in enumerate(seq_wcet)]
        tw_wcet = [tw - j*Tw for j, (_, tw) in enumerate(seq_wcet)]

        max_tr = max(tr_wcet)
        min_tr = min(tr_bcet)
        max_tw = max(tw_wcet)
        min_tw = min(tw_bcet)

        read_offset = min_tr
        read_jitter = max_tr - min_tr
        write_offset= min_tw
        write_jitter= max_tw - min_tw

        selected_read_offsets.append(read_offset)
        read_jitters.append(read_jitter)
        selected_write_offsets.append(write_offset)
        write_jitters.append(write_jitter)
        
    return read_jitters, write_jitters, selected_read_offsets, selected_write_offsets



def compare_our_passive_active(jitters, num_chains, num_repeats, random_seed, periods):
    """
    Compares the "Passive Analysis" and "Active Analysis" (adjustment) experiments from the RTSS 2025 paper.

    arguments:
        jitters: List of jitter values
        num_chains: List of number of task chains
        num_repeats: Number of repeats
        random_seed: Random seed
        periods: List of periods

    return:
        tuple: A tuple containing all results (passive result, passive failed result, passive final result, active result, active failed result, active final result)
    """
    TOLERANCE = 1e-9
    # preparing list for storing result
    results = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    final = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    false_results = {num_tasks: {per_jitter: 0 for per_jitter in jitters} for num_tasks in num_chains}
    
    results_active = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    final_active = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    false_results_active = {num_tasks: {per_jitter: 0 for per_jitter in jitters} for num_tasks in num_chains}

    for i in range(num_repeats):
        random.seed(random_seed)

        for num_tasks in num_chains:
            # Random generation matches our periods and read/write offsets
            selected_periods, selected_read_offsets, selected_write_offsets = generate_periods_and_offsets(num_tasks, periods)

            for per_jitter in jitters:
                # Passive analysis
                print(f"=========For evaluation passive our========= num_tasks {num_tasks} per_jitter {per_jitter} Repeat {i} random_seed {random_seed} ==================")
                final_e2e_max, max_reaction_time,  final_r, final_w, tasks= run_analysis_passive_our(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter)
                
                if final_e2e_max != 0:
                    # Sec. VI.
                    # R = DFFbase/DFFbound
                    r = max_reaction_time / final_e2e_max
                    if r > 1 + TOLERANCE:  
                        exceed = "exceed"
                    else:
                        exceed = "safe"
                else:
                    # Returns 0 if the algorithm fails
                    r = None
                    exceed = None
                    false_results[num_tasks][per_jitter] += 1  

                results[num_tasks][per_jitter].append((final_e2e_max, max_reaction_time,r,tasks,random_seed,exceed))
                final[num_tasks][per_jitter].append((final_r, final_w))

                # Active analysis
                print(f"=========For evaluation active our========= num_tasks {num_tasks} per_jitter {per_jitter} Repeat {i} random_seed {random_seed} ==================")
                final_e2e_max_active, max_reaction_time_active, final_r_active, final_w_active, tasks_active, adjusted, inserted = run_analysis_active_our(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter)

                if final_e2e_max_active != 0:
                    # Sec. VI.
                    # R = DFFbase/DFFbound
                    r_active = max_reaction_time_active / final_e2e_max_active
                    if r_active > 1 + TOLERANCE:  
                        exceed_active = "exceed"
                    else:
                        exceed_active = "safe"
                else:
                    r_active = None
                    exceed_active = None
                    false_results_active[num_tasks][per_jitter] += 1  # algorithm failed

                results_active[num_tasks][per_jitter].append((final_e2e_max_active, max_reaction_time_active, r_active, tasks_active, random_seed, exceed_active, adjusted, inserted))
                final_active[num_tasks][per_jitter].append((final_r_active, final_w_active))

        random_seed += 1
    # Save false results
    for num_tasks in num_chains:
        for per_jitter in jitters:
            false_percentage = (false_results[num_tasks][per_jitter] / num_repeats)
            false_results[num_tasks][per_jitter] = false_percentage

            false_percentage_active = (false_results_active[num_tasks][per_jitter] / num_repeats)
            false_results_active[num_tasks][per_jitter] = false_percentage_active

    return results, false_results, final, results_active, false_results_active, final_active


def compare_our_passive_active(jitters, num_chains, num_repeats, random_seed, periods):
    """
    Compares the "Passive Analysis" and "Active Analysis" (adjustment) experiments from the RTSS 2025 paper.

    arguments:
        jitters: List of jitter values
        num_chains: List of number of task chains
        num_repeats: Number of repeats
        random_seed: Random seed
        periods: List of periods

    return:
        tuple: A tuple containing all results (passive result, passive failed result, passive final result, active result, active failed result, active final result)
    """
    TOLERANCE = 1e-9
    # preparing list for storing result
    results = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    final = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    false_results = {num_tasks: {per_jitter: 0 for per_jitter in jitters} for num_tasks in num_chains}
    
    results_active = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    final_active = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    false_results_active = {num_tasks: {per_jitter: 0 for per_jitter in jitters} for num_tasks in num_chains}

    for i in range(num_repeats):
        random.seed(random_seed)

        for num_tasks in num_chains:
            # Random generation matches our periods and read/write offsets
            selected_periods, selected_read_offsets, selected_write_offsets = generate_periods_and_offsets(num_tasks, periods)

            for per_jitter in jitters:
                # Passive analysis
                print(f"=========For evaluation passive our========= num_tasks {num_tasks} per_jitter {per_jitter} Repeat {i} random_seed {random_seed} ==================")
                final_e2e_max, max_reaction_time,  final_r, final_w, tasks= run_analysis_passive_our(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter)
                
                if final_e2e_max != 0:
                    # Sec. VI.
                    # R = DFFbase/DFFbound
                    r = max_reaction_time / final_e2e_max
                    if r > 1 + TOLERANCE:  
                        exceed = "exceed"
                    else:
                        exceed = "safe"
                else:
                    # Returns 0 if the algorithm fails
                    r = None
                    exceed = None
                    false_results[num_tasks][per_jitter] += 1  

                results[num_tasks][per_jitter].append((final_e2e_max, max_reaction_time,r,tasks,random_seed,exceed))
                final[num_tasks][per_jitter].append((final_r, final_w))

                # Active analysis
                print(f"=========For evaluation active our========= num_tasks {num_tasks} per_jitter {per_jitter} Repeat {i} random_seed {random_seed} ==================")
                final_e2e_max_active, max_reaction_time_active, final_r_active, final_w_active, tasks_active, adjusted, inserted = run_analysis_active_our(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter)

                if final_e2e_max_active != 0:
                    # Sec. VI.
                    # R = DFFbase/DFFbound
                    r_active = max_reaction_time_active / final_e2e_max_active
                    if r_active > 1 + TOLERANCE:  
                        exceed_active = "exceed"
                    else:
                        exceed_active = "safe"
                else:
                    r_active = None
                    exceed_active = None
                    false_results_active[num_tasks][per_jitter] += 1  # algorithm failed

                results_active[num_tasks][per_jitter].append((final_e2e_max_active, max_reaction_time_active, r_active, tasks_active, random_seed, exceed_active, adjusted, inserted))
                final_active[num_tasks][per_jitter].append((final_r_active, final_w_active))

        random_seed += 1
    # Save false results
    for num_tasks in num_chains:
        for per_jitter in jitters:
            false_percentage = (false_results[num_tasks][per_jitter] / num_repeats)
            false_results[num_tasks][per_jitter] = false_percentage

            false_percentage_active = (false_results_active[num_tasks][per_jitter] / num_repeats)
            false_results_active[num_tasks][per_jitter] = false_percentage_active

    return results, false_results, final, results_active, false_results_active, final_active



def compare_Gunzel_IC(num_chains, num_repeats, random_seed, periods):
    """
    Compares our (passive, active) and paper [20] implicit communication (Gunzel IC) experiments.
    [20] M. Günzel, K.-H. Chen, N. Ueter, G. von der Brüggen, M. Dürr, and J.-J. Chen, “Timing analysis of asynchronized distributed cause- effect chains,” in Real Time and Embedded Technology and Applications Symposium (RTAS), 2021.

    arguments:
        num_chains: List of number of task chains
        num_repeats: Number of repeats
        random_seed: Random seed
        periods: List of periods

    return:
        tuple: A tuple containing all results (passive result, passive failed result, passive final result, active result, active failed result, active final result)
    """
    TOLERANCE = 1e-9
    # preparing list for storing result
    results = {num_tasks: [] for num_tasks in num_chains}
    final = {num_tasks: [] for num_tasks in num_chains}
    false_results = {num_tasks:  0  for num_tasks in num_chains}
    
    results_active = {num_tasks:  [] for num_tasks in num_chains}
    final_active = {num_tasks:  []  for num_tasks in num_chains}
    false_results_active = {num_tasks:  0  for num_tasks in num_chains}

    for i in range(num_repeats):
        random.seed(random_seed)

        for num_tasks in num_chains:
            # Generate Gunzel task and calculate IC maximum reaction time
            ic, selected_periods, schedule_wcet, task_set, schedule_bcet, new_task_set,run_time_G = run_analysis_Gunzel_IC(num_tasks, periods)
            read_jitters, write_jitters,  selected_read_offsets, selected_write_offsets = convert_to_our_offsets(schedule_wcet, task_set, schedule_bcet, new_task_set)

            # Compare passive analysis between our and Gunzel IC
            print(f"=========For evaluation passive Gunzel IC========= num_tasks {num_tasks} Repeat {i} random_seed {random_seed} ==================")
            t_our_0 = time.perf_counter()
            # Analyzing the Gunzel tasks using our passive analysis (RTSS'2025 Alg.2)
            final_e2e_max, final_r, final_w, tasks = run_analysis_passive_Gunzel_IC(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, read_jitters, write_jitters )
            t_our_1 = time.perf_counter()
            run_time_our = t_our_1 - t_our_0

            if final_e2e_max != 0:
                # Sec. VI.
                # R = DFFbase/DFFbound
                r = ic  / final_e2e_max
                if r > 1 + TOLERANCE:  
                    exceed = "exceed"
                else:
                    exceed = "safe"
            else:
                r = None
                exceed = None
                false_results[num_tasks] += 1  # algorithm failed

            results[num_tasks].append((final_e2e_max, ic,r,tasks,random_seed,exceed,run_time_our,run_time_G))
            final[num_tasks].append((final_r, final_w))

            # Compare active analysis between our and Gunzel IC
            print(f"=========For evaluation active Gunzel IC========= num_tasks {num_tasks} Repeat {i} random_seed {random_seed} ==================")
            t_our_active_0 = time.perf_counter()
            # Analyzing the Gunzel tasks using our active analysis
            final_e2e_max_active, final_r_active, final_w_active, tasks_active, adjusted, inserted = run_analysis_active_Gunzel_IC(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, read_jitters, write_jitters )
            t_our_active_1 = time.perf_counter()
            run_time_our_active = t_our_active_1 - t_our_active_0

            if final_e2e_max_active != 0:
                # Sec. VI.
                # R = DFFbase/DFFbound
                r_active = ic / final_e2e_max_active
                if r_active > 1 + TOLERANCE:  
                    exceed_active = "exceed"
                else:
                    exceed_active = "safe"
            else:
                r_active = None
                exceed_active = None
                false_results_active[num_tasks] += 1  # algorithm failed

            results_active[num_tasks].append((final_e2e_max_active, ic, r_active, tasks_active, random_seed, exceed_active, adjusted, inserted,run_time_our_active,run_time_G))
            final_active[num_tasks].append((final_r_active, final_w_active))

        random_seed += 1

    # Save false results
    for num_tasks in num_chains:
        false_percentage = (false_results[num_tasks] / num_repeats)
        false_results[num_tasks]= false_percentage

        false_percentage_active = (false_results_active[num_tasks] / num_repeats)
        false_results_active[num_tasks] = false_percentage_active

    return results, false_results, final, results_active, false_results_active, final_active



def compare_Gunzel_LET(jitters, num_chains, num_repeats, random_seed, periods):
    """
    Compares our (passive, active) and paper [20] LET communication (Gunzel LET) experiments.

    arguments:
        jitters: zero(LET)
        num_chains: List of number of task chains
        num_repeats: Number of repeats
        random_seed: Random seed
        periods: List of periods

    return:
        tuple: A tuple containing all results (passive result, passive failed result, passive final result, active result, active failed result, active final result)
    """
    TOLERANCE = 1e-9
    # preparing list for storing result
    results = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    final = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    false_results = {num_tasks: {per_jitter: 0 for per_jitter in jitters} for num_tasks in num_chains}
    
    results_active = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    final_active = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    false_results_active = {num_tasks: {per_jitter: 0 for per_jitter in jitters} for num_tasks in num_chains}
    
    for i in range(num_repeats):
        random.seed(random_seed)

        for num_tasks in num_chains:
            # Generate our LET tasks' offsets...
            selected_periods, selected_read_offsets, selected_write_offsets = generate_LET(num_tasks, periods)

            for per_jitter in jitters:
                # Compare passive analysis between our and Gunzel LET
                print(f"=========For evaluation passive Gunzel LET========= num_tasks {num_tasks} per_jitter {per_jitter} Repeat {i} random_seed {random_seed} ==================")
                t_our_0 = time.perf_counter()
                # Analyzing our LET tasks using our passive analysis (RTSS'2025 Alg.2)
                final_e2e_max, final_r, final_w, tasks = run_analysis_passive_Gunzel_LET(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter)
                t_our_1 = time.perf_counter()
                run_time_our = t_our_1 - t_our_0

                t_G_0 = time.perf_counter()
                # Analyzing our LET tasks using Gunzel LET
                let = run_analysis_Gunzel_LET(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter)
                t_G_1 = time.perf_counter()
                run_time_G = t_G_1 - t_G_0

                if final_e2e_max != 0:
                    # Sec. VI.
                    # R = DFFbase/DFFbound
                    r = let / final_e2e_max
                    if r > 1 + TOLERANCE:  
                        exceed = "exceed"
                    else:
                        exceed = "safe"
                else:
                    r = None
                    exceed = None
                    false_results[num_tasks][per_jitter] += 1  # algorithm failed

                results[num_tasks][per_jitter].append((final_e2e_max, let,r,tasks,random_seed,exceed,run_time_our,run_time_G))
                final[num_tasks][per_jitter].append((final_r, final_w))

                # Compare active analysis between our and Gunzel LET
                print(f"=========For evaluation active Gunzel LET========= num_tasks {num_tasks} per_jitter {per_jitter} Repeat {i} random_seed {random_seed} ==================")
                t_our_active_0 = time.perf_counter()
                # Analyzing our LET tasks using our active analysis 
                final_e2e_max_active, final_r_active, final_w_active, tasks_active, adjusted, inserted = run_analysis_active_Gunzel_LET(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter)
                t_our_active_1 = time.perf_counter()
                run_time_our_active = t_our_active_1 - t_our_active_0

                if final_e2e_max_active != 0:
                    # Sec. VI.
                    # R = DFFbase/DFFbound
                    r_active = let / final_e2e_max_active
                    if r_active > 1 + TOLERANCE:  
                        exceed_active = "exceed"
                    else:
                        exceed_active = "safe"
                else:
                    r_active = None
                    exceed_active = None
                    false_results_active[num_tasks][per_jitter] += 1  # algorithm failed

                results_active[num_tasks][per_jitter].append((final_e2e_max_active, let, r_active, tasks_active, random_seed, exceed_active, adjusted, inserted, run_time_G,run_time_our_active))
                final_active[num_tasks][per_jitter].append((final_r_active, final_w_active))

        random_seed += 1

    # Save false results
    for num_tasks in num_chains:
        for per_jitter in jitters:
            false_percentage = (false_results[num_tasks][per_jitter] / num_repeats)
            false_results[num_tasks][per_jitter] = false_percentage

            false_percentage_active = (false_results_active[num_tasks][per_jitter] / num_repeats)
            false_results_active[num_tasks][per_jitter] = false_percentage_active

    return results, false_results, final, results_active, false_results_active, final_active



def compare_our_active_add(jitters, num_chains, num_repeats, random_seed, periods):
    TOLERANCE = 1e-9
    # preparing list for storing result
    results_active = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    final_active = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    false_results_active = {num_tasks: {per_jitter: 0 for per_jitter in jitters} for num_tasks in num_chains}

    results_add = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    final_add = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    false_results_add = {num_tasks: {per_jitter: 0 for per_jitter in jitters} for num_tasks in num_chains}


    for i in range(num_repeats):
        random.seed(random_seed)

        for num_tasks in num_chains:
            # Random generation matches our periods and read/write offsets
            selected_periods, selected_read_offsets, selected_write_offsets = generate_periods_and_offsets(num_tasks, periods)

            for per_jitter in jitters:
                # Active analysis
                print(f"=========For evaluation active our========= num_tasks {num_tasks} per_jitter {per_jitter} Repeat {i} random_seed {random_seed} ==================")
                final_e2e_max_active, max_reaction_time_active, final_r_active, final_w_active, tasks_active, adjusted, inserted = run_analysis_active_our(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter)

                if final_e2e_max_active != 0:
                    # Sec. VI.
                    # R = DFFbase/DFFbound
                    r_active = max_reaction_time_active / final_e2e_max_active
                    if r_active > 1 + TOLERANCE:  
                        exceed_active = "exceed"
                    else:
                        exceed_active = "safe"
                else:
                    r_active = None
                    exceed_active = None
                    false_results_active[num_tasks][per_jitter] += 1  # algorithm failed

                results_active[num_tasks][per_jitter].append((final_e2e_max_active, max_reaction_time_active, r_active, tasks_active, random_seed, exceed_active, adjusted, inserted))
                final_active[num_tasks][per_jitter].append((final_r_active, final_w_active))

                # Passive analysis
                print(f"=========For evaluation active add  our========= num_tasks {num_tasks} per_jitter {per_jitter} Repeat {i} random_seed {random_seed} ==================")
                final_e2e_max_add, max_reaction_time_add,  final_r_add, final_w_add, tasks_add, added= run_analysis_active_our_add(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter)
                
                if final_e2e_max_add != 0:
                    # Sec. VI.
                    # R = DFFbase/DFFbound
                    r_add = max_reaction_time_add / final_e2e_max_add
                    if r_add > 1 + TOLERANCE:  
                        exceed_add = "exceed"
                    else:
                        exceed_add = "safe"
                else:
                    # Returns 0 if the algorithm fails
                    r_add = None
                    exceed_add = None
                    false_results_add[num_tasks][per_jitter] += 1  

                results_add[num_tasks][per_jitter].append((final_e2e_max_add, max_reaction_time_add, r_add, tasks_add, random_seed, exceed_add, added))
                final_add[num_tasks][per_jitter].append((final_r_add, final_w_add))

        random_seed += 1
    # Save false results
    for num_tasks in num_chains:
        for per_jitter in jitters:
            false_percentage_active = (false_results_active[num_tasks][per_jitter] / num_repeats)
            false_results_active[num_tasks][per_jitter] = false_percentage_active

            false_percentage_add= (false_results_add[num_tasks][per_jitter] / num_repeats)
            false_results_add[num_tasks][per_jitter] = false_percentage_add

    return results_active, false_results_active, final_active, results_add, false_results_add, final_add




def compare_our_passive_order(jitters, num_chains, num_repeats, random_seed, periods):
    TOLERANCE = 1e-9
    # preparing list for storing result
    results = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    final = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    false_results = {num_tasks: {per_jitter: 0 for per_jitter in jitters} for num_tasks in num_chains}
    
    results_order = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    final_order = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    false_results_order = {num_tasks: {per_jitter: 0 for per_jitter in jitters} for num_tasks in num_chains}

    for i in range(num_repeats):
        random.seed(random_seed)

        for num_tasks in num_chains:
            # Random generation matches our periods and read/write offsets
            selected_periods, selected_read_offsets, selected_write_offsets = generate_periods_and_offsets(num_tasks, periods)

            for per_jitter in jitters:
                # Passive analysis
                print(f"=========For evaluation passive our========= num_tasks {num_tasks} per_jitter {per_jitter} Repeat {i} random_seed {random_seed} ==================")
                final_e2e_max, max_reaction_time,  final_r, final_w, tasks= run_analysis_passive_our(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter)
                
                if final_e2e_max != 0:
                    # Sec. VI.
                    # R = DFFbase/DFFbound
                    r = max_reaction_time / final_e2e_max
                    if r > 1 + TOLERANCE:  
                        exceed = "exceed"
                    else:
                        exceed = "safe"
                else:
                    # Returns 0 if the algorithm fails
                    r = None
                    exceed = None
                    false_results[num_tasks][per_jitter] += 1  

                results[num_tasks][per_jitter].append((final_e2e_max, max_reaction_time,r,tasks,random_seed,exceed))
                final[num_tasks][per_jitter].append((final_r, final_w))

                # order analysis
                print(f"=========For evaluation order our========= num_tasks {num_tasks} per_jitter {per_jitter} Repeat {i} random_seed {random_seed} ==================")
                final_e2e_max_order, max_reaction_time_order, final_r_order, final_w_order, tasks_order, best_merge_pair = run_analysis_passive_our_order (num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter)

                if final_e2e_max_order != 0:
                    # Sec. VI.
                    # R = DFFbase/DFFbound
                    r_order = max_reaction_time_order / final_e2e_max_order
                    if r_order > 1 + TOLERANCE:  
                        exceed_order = "exceed"
                    else:
                        exceed_order = "safe"
                else:
                    r_order = None
                    exceed_order = None
                    false_results_order[num_tasks][per_jitter] += 1  # algorithm failed

                results_order[num_tasks][per_jitter].append((final_e2e_max_order, max_reaction_time_order, r_order, tasks_order, random_seed, exceed_order, best_merge_pair))
                final_order[num_tasks][per_jitter].append((final_r_order, final_w_order))

        random_seed += 1
    # Save false results
    for num_tasks in num_chains:
        for per_jitter in jitters:
            false_percentage = (false_results[num_tasks][per_jitter] / num_repeats)
            false_results[num_tasks][per_jitter] = false_percentage

            false_percentage_order = (false_results_order[num_tasks][per_jitter] / num_repeats)
            false_results_order[num_tasks][per_jitter] = false_percentage_order

    return results, false_results, final, results_order, false_results_order, final_order




def compare_our_passive_add_order(jitters, num_chains, num_repeats, random_seed, periods):
    TOLERANCE = 1e-9
    # preparing list for storing result
    results = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    final = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    false_results = {num_tasks: {per_jitter: 0 for per_jitter in jitters} for num_tasks in num_chains}
    
    results_active = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    final_active = {num_tasks: {per_jitter: [] for per_jitter in jitters} for num_tasks in num_chains}
    false_results_active = {num_tasks: {per_jitter: 0 for per_jitter in jitters} for num_tasks in num_chains}

    for i in range(num_repeats):
        random.seed(random_seed)

        for num_tasks in num_chains:
            # Random generation matches our periods and read/write offsets
            selected_periods, selected_read_offsets, selected_write_offsets = generate_periods_and_offsets(num_tasks, periods)

            for per_jitter in jitters:
                # Passive analysis
                print(f"=========For evaluation passive order ========= num_tasks {num_tasks} per_jitter {per_jitter} Repeat {i} random_seed {random_seed} ==================")
                final_e2e_max, max_reaction_time,  final_r, final_w, tasks, best_merge_pair= run_analysis_passive_our_order(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter)
                
                if final_e2e_max != 0:
                    # Sec. VI.
                    # R = DFFbase/DFFbound
                    r = max_reaction_time / final_e2e_max
                    if r > 1 + TOLERANCE:  
                        exceed = "exceed"
                    else:
                        exceed = "safe"
                else:
                    # Returns 0 if the algorithm fails
                    r = None
                    exceed = None
                    false_results[num_tasks][per_jitter] += 1  

                results[num_tasks][per_jitter].append((final_e2e_max, max_reaction_time,r,tasks,random_seed,exceed,best_merge_pair))
                final[num_tasks][per_jitter].append((final_r, final_w))

                # Active analysis
                print(f"=========For evaluation active add order========= num_tasks {num_tasks} per_jitter {per_jitter} Repeat {i} random_seed {random_seed} ==================")
                final_e2e_max_active, max_reaction_time_active, final_r_active, final_w_active, tasks_active, best_merge_pair, added  = run_analysis_active_our_add_order(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter)

                if final_e2e_max_active != 0:
                    # Sec. VI.
                    # R = DFFbase/DFFbound
                    r_active = max_reaction_time_active / final_e2e_max_active
                    if r_active > 1 + TOLERANCE:  
                        exceed_active = "exceed"
                    else:
                        exceed_active = "safe"
                else:
                    r_active = None
                    exceed_active = None
                    false_results_active[num_tasks][per_jitter] += 1  # algorithm failed

                results_active[num_tasks][per_jitter].append((final_e2e_max_active, max_reaction_time_active, r_active, tasks_active, random_seed, exceed_active, best_merge_pair, added ))
                final_active[num_tasks][per_jitter].append((final_r_active, final_w_active))

        random_seed += 1
    # Save false results
    for num_tasks in num_chains:
        for per_jitter in jitters:
            false_percentage = (false_results[num_tasks][per_jitter] / num_repeats)
            false_results[num_tasks][per_jitter] = false_percentage

            false_percentage_active = (false_results_active[num_tasks][per_jitter] / num_repeats)
            false_results_active[num_tasks][per_jitter] = false_percentage_active

    return results, false_results, final, results_active, false_results_active, final_active




def append_to_common_csv(csv_file, common_csv_file):
    """
    Append the tmp.csv file generated from a single experiment to the common_csv_file table.
    arguments:
        csv_file: The temporary CSV file generated from a single experiment
        common_csv_file: The common CSV file to which results are appended
    return:
        None
    """
    try:
        df_current = pd.read_csv(csv_file)
        
        if os.path.exists(common_csv_file):
            df_common = pd.read_csv(common_csv_file)
            df_combined = pd.concat([df_common, df_current], ignore_index=True)
        else:
            df_combined = df_current
        
        df_combined.to_csv(common_csv_file, index=False)
        print(f"Results appended to common CSV: {common_csv_file}")
        
    except Exception as e:
        print(f"Error appending to common CSV: {e}")



def compare_plots(csv_files, num_repeats, random_seed, timestamp):
    """
    Comparison charts for our passive and active experiments
        1) Failure rate vs. number of tasks/jitter (compare_percent)
        2) Ratio (our/Gunzel) histogram (compare_histogram)
    arguments:
        csv_files: List of CSV files to be compared
        num_repeats: Number of repeats
        random_seed: Random seed
        timestamp: Timestamp for naming the output files
    return:
        None
    """
    folder_name = f"{num_repeats}_{random_seed}_{timestamp}"
    folder_path = os.path.join("compare/", folder_name)

    os.makedirs(folder_path, exist_ok=True)
    
    compare_percent_plot_name = os.path.join(folder_path,  f"compare_percent_{num_repeats}_{random_seed}_{timestamp}.png")
    compare_histogram_plot_name = os.path.join(folder_path, f"compare_R_{num_repeats}_{random_seed}_{timestamp}.png")

    compare_false_percent_our(csv_files, compare_percent_plot_name)
    compare_plot_histogram_our(csv_files, compare_histogram_plot_name)
    
    print(f"Compare percent plots generated and saved to {compare_percent_plot_name} and {compare_histogram_plot_name}")



def run_Gunzel_IC(periods, num_chains, random_seed, num_repeats, common_csv_passive, common_csv_active):
    """
    Implicit communication comparison experiment (passive/active/Gunzel IC)
    please see RTSS'2025 fig.11, 13.
    arguments:
        random_seed: Random seed
        num_repeats: Number of repeats
        common_csv_passive: Common CSV file for passive results
        common_csv_active: Common CSV file for active results
    return:
        None
    """
    timestamp = datetime.datetime.fromtimestamp(int(time.time())).strftime("%Y%m%d_%H%M%S")

    results, false_results, final, results_active, false_results_active, final_active = compare_Gunzel_IC(num_chains, num_repeats, random_seed, periods)  

    csv_file = output_passive_Gunzel_IC(num_repeats, random_seed, timestamp, results, false_results, num_chains)
    csv_file_active = output_active_Gunzel_IC(num_repeats, random_seed, timestamp, results_active, false_results_active, num_chains)
    append_to_common_csv(csv_file, common_csv_passive)
    append_to_common_csv(csv_file_active, common_csv_active)



def run_Gunzel_LET(periods, num_chains, jitters, random_seed, num_repeats, common_csv_passive, common_csv_active):    
    """
    LET communication comparison experiment (passive-jitter=0/active-jitter=0/Gunzel LET)
    arguments:
        random_seed: Random seed
        num_repeats: Number of repeats
        common_csv_passive: Common CSV file for passive results
        common_csv_active: Common CSV file for active results
    return:
        None
    """
    timestamp = datetime.datetime.fromtimestamp(int(time.time())).strftime("%Y%m%d_%H%M%S")

    results, false_results, final, results_active, false_results_active, final_active = compare_Gunzel_LET(jitters, num_chains, num_repeats, random_seed, periods)

    csv_file = output_passive_Gunzel_LET(num_repeats, random_seed, timestamp, results, false_results, num_chains,jitters)
    csv_file_active = output_active_Gunzel_LET(num_repeats, random_seed, timestamp, results_active, false_results_active, num_chains,jitters)

    append_to_common_csv(csv_file, common_csv_passive)
    append_to_common_csv(csv_file_active, common_csv_active)




def run_our_passive_active(periods, num_chains, jitters, random_seed, num_repeats, common_csv_passive, common_csv_active):
    """
    LET(jitter=0)/Implicit communication(IC) comparison experiment (passive/active)
    please see RTSS'2025 fig.10, 12.
    arguments:
        random_seed: Random seed
        num_repeats: Number of repeats
        common_csv_passive: Common CSV file for passive results
        common_csv_active: Common CSV file for active results
    return:
        None
    """
    
    timestamp = datetime.datetime.fromtimestamp(int(time.time())).strftime("%Y%m%d_%H%M%S")
        
    results, false_results, final, results_active, false_results_active, final_active = compare_our_passive_active(
        jitters, num_chains, num_repeats, random_seed, periods)

    csv_file = output_passive_our(num_repeats, random_seed, timestamp, results, false_results, num_chains, jitters)
    csv_file_active = output_active_our(num_repeats, random_seed, timestamp, results_active, false_results_active, num_chains, jitters)
    append_to_common_csv(csv_file, common_csv_passive)
    append_to_common_csv(csv_file_active, common_csv_active)



def run_our_active_add(periods, num_chains, jitters,random_seed, num_repeats, common_csv_active, common_csv_add):
    
    timestamp = datetime.datetime.fromtimestamp(int(time.time())).strftime("%Y%m%d_%H%M%S")
        
    results_active, false_results_active, final_active, results_add, false_results_add, final_add = compare_our_active_add(
        jitters, num_chains, num_repeats, random_seed, periods)

    csv_file_active = output_active_our(num_repeats, random_seed, timestamp, results_active, false_results_active, num_chains, jitters)
    csv_file_add = output_active_our_add(num_repeats, random_seed, timestamp, results_add, false_results_add, num_chains, jitters)

    append_to_common_csv(csv_file_active, common_csv_active)
    append_to_common_csv(csv_file_add, common_csv_add)



def run_our_passive_order(periods, num_chains, jitters, random_seed, num_repeats,  common_csv_passive, common_csv_passive_order):
    
    timestamp = datetime.datetime.fromtimestamp(int(time.time())).strftime("%Y%m%d_%H%M%S")
        
    results, false_results, final, results_order, false_results_order, final_order = compare_our_passive_order(
        jitters, num_chains, num_repeats, random_seed, periods)

    csv_file_passive = output_passive_our(num_repeats, random_seed, timestamp, results, false_results, num_chains, jitters)
    csv_file_passive_order = output_passive_our_order(num_repeats, random_seed, timestamp, results_order, false_results_order, num_chains, jitters)

    append_to_common_csv(csv_file_passive, common_csv_passive)
    append_to_common_csv(csv_file_passive_order, common_csv_passive_order)



def run_our_passive_add_order(periods, num_chains, jitters, random_seed, num_repeats, common_csv_passive, common_csv_active):
    timestamp = datetime.datetime.fromtimestamp(int(time.time())).strftime("%Y%m%d_%H%M%S")
        
    results, false_results, final, results_active, false_results_active, final_active = compare_our_passive_add_order(
        jitters, num_chains, num_repeats, random_seed, periods)

    csv_file = output_passive_our_order(num_repeats, random_seed, timestamp, results, false_results, num_chains, jitters)
    csv_file_active = output_active_our_add_order(num_repeats, random_seed, timestamp, results_active, false_results_active, num_chains, jitters)
    append_to_common_csv(csv_file, common_csv_passive)
    append_to_common_csv(csv_file_active, common_csv_active)







def main():
    print("Raw sys.argv:", sys.argv)
    parser = argparse.ArgumentParser(description='Compare our_passive, our_active, GunzelIC, GunzelLET')
    parser.add_argument('random_seed', type=int, help='Random seed for the experiment')
    parser.add_argument('num_repeats', type=int, help='Number of repeats for the experiment')

    # Algorithm selection
    parser.add_argument('--alg', choices=['IC', 'LET', 'RTSS', 'ADD', 'PAORDER', 'ADORDER'], default='RTSS',
                        help='Which algorithm to run')

    # Configurable parameters with smart defaults
    parser.add_argument('--periods', type=int, nargs='+', required=True)
    parser.add_argument('--jitters', type=float, nargs='+', required=True)
    parser.add_argument('--num_chains', type=int, nargs='+', required=True)

    # Output files
    parser.add_argument('--common_csv_passive', type=str, default='common_results_passive.csv')
    parser.add_argument('--common_csv_active', type=str, default='common_results_active.csv')
    parser.add_argument('--common_csv_passive_order', type=str, default='common_results_passive_order.csv')
    parser.add_argument('--common_csv_active_add', type=str, default='common_results_active_add.csv')


    parser.add_argument('--suffix', default='', help='Suffix for output files')


    args = parser.parse_args()

    # Set base defaults
    DEFAULT_PERIODS = [1, 2, 5, 10, 20, 50, 100, 200, 1000]
    DEFAULT_JITTERS_RTSS = [0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5]
    DEFAULT_NUM_CHAINS = [3, 5, 8, 10]

    # Use provided args or defaults
    periods = args.periods if args.periods is not None else DEFAULT_PERIODS
    num_chains = args.num_chains if args.num_chains is not None else DEFAULT_NUM_CHAINS

    random_seed = args.random_seed
    num_repeats = args.num_repeats
    common_csv_passive   = args.common_csv_passive
    common_csv_active = args.common_csv_active
    common_csv_active_add = args.common_csv_active_add
    common_csv_passive_order = args.common_csv_passive_order

    # Handle jitters based on algorithm
    if args.alg == 'IC':
        # IC does not use jitter; it's derived from schedule
        jitters = []
    elif args.alg == 'LET' or args.alg == 'ZEROORDER':
        # LET always uses jitter = 0
        jitters = [0]   
    else:
        jitters = args.jitters if args.jitters is not None else DEFAULT_JITTERS_RTSS
    
    alg = args.alg

    # Dispatch
    if alg == 'IC':
        # IC doesn't need jitters
        run_Gunzel_IC(periods, num_chains, random_seed, num_repeats, common_csv_passive, common_csv_active)
    elif alg == 'LET':
        run_Gunzel_LET(periods, num_chains, jitters, random_seed, num_repeats, common_csv_passive, common_csv_active)
    elif alg == 'RTSS':
        run_our_passive_active(periods, num_chains, jitters, random_seed, num_repeats, common_csv_passive, common_csv_active)
    elif alg == 'ADD':
        run_our_active_add(periods, num_chains, jitters, random_seed, num_repeats, common_csv_active, common_csv_active_add)
    elif alg == 'PAORDER':
        run_our_passive_order(periods, num_chains, jitters,random_seed, num_repeats, common_csv_passive, common_csv_passive_order)
    elif alg == 'ADORDER':
        run_our_passive_add_order(periods, num_chains, jitters, random_seed, num_repeats, common_csv_passive, common_csv_active)
    else:
        raise ValueError(f"Unsupported algorithm: {alg}")
    
if __name__ == "__main__":
    main()