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
import numpy as np
from scipy.optimize import basinhopping

from analysis_passive import Event, Task, RandomEvent
from analysis_active_add import combine_with_insertion_add


def our_chain_active_add_order(tasks):
    added = False
    n = len(tasks)
    if n < 1:
        return False

    # Single task: same as our_chain
    if n == 1:
        final_r = tasks[0].read_event
        final_w = tasks[0].write_event
        max_reaction_time = final_w.offset + final_w.maxjitter - final_r.offset + final_r.period
        return max_reaction_time, final_r, final_w, None, added

    best_write_jitter = float("inf")
    best_result = None
    best_merge_pair = None
    best_e2e = float("inf")

    # Try all initial merge positions k = 0 ... n-2
    for k in range(n - 1):

        # ---- step 1: first merge k and k+1 ----
        result = combine_with_insertion_add(tasks[k], tasks[k + 1])
        if result is False:
            continue

        r, w, added = result
        merged_task = Task(read_event=r, write_event=w, id=r.id)

        # ---- step 2: merge the whole chain sequentially ----
        current_task = None
        valid = True

        for i in range(n):
            if i == k:
                if current_task is None:
                    current_task = merged_task
                else:
                    result = combine_with_insertion_add(current_task, merged_task)
                    if result is False:
                        valid = False
                        break
                    r, w, added = result
                    current_task = Task(read_event=r, write_event=w, id=r.id)

            elif i == k + 1:
                continue  # already merged

            else:
                if current_task is None:
                    current_task = tasks[i]
                else:
                    result = combine_with_insertion_add(current_task, tasks[i])
                    if result is False:
                        valid = False
                        break
                    r, w, added = result
                    current_task = Task(read_event=r, write_event=w, id=r.id)

        if not valid or current_task is None:
            continue

        # ---- step 3: evaluate final write jitter ----
        final_write_jitter = current_task.write_event.maxjitter
        final_e2e = current_task.write_event.offset + current_task.write_event.maxjitter - current_task.read_event.offset + current_task.read_event.period

        if final_write_jitter < best_write_jitter:
            best_e2e = final_e2e
            best_write_jitter = final_write_jitter
            best_result = current_task
            best_merge_pair = (k, k + 1)  # 1-based
        elif final_write_jitter == best_write_jitter:
            if final_e2e < best_e2e:
                best_e2e = final_e2e
                best_write_jitter = final_write_jitter
                best_result = current_task
                best_merge_pair = (k , k+1)

    if best_result is None:
        return False

    # ---- step 4: compute max reaction time (Formula 39) ----
    r1n = best_result.read_event
    w1n = best_result.write_event

    # max_reaction_time = w1n.offset + w1n.maxjitter - r1n.offset + r1n.period
    max_reaction_time = best_e2e

    return max_reaction_time, r1n, w1n, best_merge_pair, added



def find_valid_task_chains(tasks):
    """
    Generate a general task chain
    Satisfy the read and write time order
    arguments:
        tasks: the task set
    return:
        task_chain: the valid task chain with read and write times
        False: if no valid task chain can be found
    """
    task_chain = []
    last_write_time = -float("inf")
    for task in tasks:
        read_event = task.read_event
        write_event = task.write_event
        
        if task is tasks[0]:
            read_instance = objective_function.iteration
        else:
            read_instance = 0

        # find the first read instance that satisfies the condition
        while True:
            read_time = read_event.get_trigger_time(read_instance)
            if read_time >= last_write_time:
                break
            read_instance += 1

        write_time = write_event.get_trigger_time(read_instance)

        read_event.read_time = read_time
        write_event.write_time = write_time

        task_chain.append((read_event, read_time, read_instance))
        task_chain.append((write_event, write_time, read_instance))

        last_write_time = write_time

    # check if the task chain is valid
    if len(task_chain) == len(tasks) * 2:
        return task_chain
    else:
        return False



def calculate_reaction_time(task_chain):
    """
    Calculate the reaction time of the general task chain
    arguments:
        task_chain: the valid task chain with read and write times
    return:
        reaction_time: the reaction time of the task chain
    """
    first_read_time = task_chain[0][1]
    last_write_time = task_chain[-1][1]
    reaction_time = last_write_time - first_read_time +  task_chain[0][0].period

    return reaction_time  



def objective_function(x, tasks):
    """
    The handle function of general task chain calculation
    Objective function for optimization
    arguments:
        x: the decision variable (jitter of read and write events)
        tasks: the task set
    return:
        -max_reaction_time: the negative of the maximum reaction time of the chain (for minimization)
        float("inf"): if no valid task chain can be found
    """
    num_tasks = len(tasks)
    for i in range(num_tasks):
        tasks[i].read_event.random_jitter = x[i]
        tasks[i].write_event.random_jitter = x[i + num_tasks]

    task_chain = find_valid_task_chains(tasks)

    if task_chain:
        max_reaction_time = calculate_reaction_time(task_chain)

        objective_function.iteration += 1
        results_function.append(max_reaction_time)
        return -max_reaction_time
    else:
        return float("inf")
    

def take_step(x, bounds):
    """
    The handle function of general task chain calculation
    arguments:
        x: the decision variable (jitter of read and write events)
        bounds: the bounds of the decision variable
    return:
        new_x: the new decision variable after taking a step
    """
    new_x = x.copy()
    for i in range(len(x)):
        lower, upper = bounds[i]
        new_x[i] = random.uniform(lower, upper)
    return new_x


def accept_test(f_new, x_new, f_old, x_old, tasks, bounds, **kwargs):
    """
    The handle function of general task chain calculation
    check if the new solution is within bounds
    arguments:
        f_new: the new objective function value
        x_new: the new decision variable (jitter of read and write events)
        f_old: the old objective function value
        x_old: the old decision variable (jitter of read and write events)
        tasks: the task set
        bounds: the bounds of the decision variable
    return:
        True: if the new solution is within bounds
        False: if the new solution is out of bounds 
    """
    for i, (lower, upper) in enumerate(bounds):
        if not (lower <= x_new[i] <= upper):
            return False
    return True
    


def maximize_reaction_time(tasks):
    """
    Maximize the reaction time of the general task chain
    arguments:
        tasks: the task set
    return:         
        max_reaction_time: the maximum reaction time of the chain
    """
    bounds = [(0, 0)] * (len(tasks) * 2)
    initial_guess = [0] * len(tasks) * 2
    for i, task in enumerate(tasks):
        bounds[i] = (0, task.read_event.maxjitter)
        bounds[i+ len(tasks)] = (0, task.write_event.maxjitter)
        # guess the initial value : random jitter of read and write events
        initial_guess[i] = random.uniform(0, task.read_event.maxjitter)
        initial_guess[i + len(tasks)] = random.uniform(0, task.write_event.maxjitter)

    minimizer_kwargs = {"method": "L-BFGS-B", "bounds": bounds}

    objective_function.iteration = 0

    def objective(x):
        return objective_function(x, tasks)
    def accept(f_new, x_new, f_old, x_old, **kwargs):
        return accept_test(f_new, x_new, f_old, x_old, tasks, bounds, **kwargs)

    # Use basinhopping to find the global maximum reaction time
    result = basinhopping(
        objective,
        initial_guess,
        minimizer_kwargs=minimizer_kwargs,
        niter=1,
        T=1.0,
        stepsize=1.0,  # Step size for the random walk
        interval=50,  # Interval for the random walk
        niter_success=10,  # Iteration bound
        # stepsize=0.01,
        take_step=lambda x: take_step(x, bounds),
        accept_test=accept
    )
    max_reaction_time = -result.fun
    
    return max_reaction_time



results_function = []


def run_analysis_active_our_add_order(num_tasks, periods,read_offsets,write_offsets, per_jitter):
    global results_function
    results_function = []  

    tasks = RandomEvent(num_tasks, periods,read_offsets,write_offsets, per_jitter).tasks

    final = our_chain_active_add_order(tasks)
    
    new_tasks = tasks
    if final is False:
        final_e2e_max = 0
        final_r = None
        final_w = None
        best_merge_pair = 0
        added = False
    else:
        final_e2e_max = final[0]
        final_r = final[1]
        final_w = final[2]
        best_merge_pair = final[3]
        added = final[4]


    # check if the final result is valid
    reaction_time_a = maximize_reaction_time(new_tasks)
    reaction_time_b = max(results_function)
    max_reaction_time = max(reaction_time_a, reaction_time_b)

    return final_e2e_max, max_reaction_time, final_r, final_w, new_tasks, best_merge_pair, added



# test the code
if __name__ == "__main__":
    num_tasks = 1 
    periods = [1, 2, 5, 10, 20, 50, 100, 200, 1000]
    
    per_jitter = 0 # percent jitter

    selected_periods = [5]
    selected_read_offsets = [0]
    selected_write_offsets = [5]

    print(selected_periods)
    print(selected_read_offsets)
    print(selected_write_offsets)

    tasks = RandomEvent(num_tasks, selected_periods,selected_read_offsets,selected_write_offsets, per_jitter).tasks

    final = our_chain_active_add_order(tasks)
    final_e2e_max = final[0]
    
    print(final_e2e_max)


