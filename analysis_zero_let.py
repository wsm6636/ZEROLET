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


import math
from functools import reduce
from collections import defaultdict
import random


"""an event"""
class Event:
    """
    Creates an event represented by ID, type, period, offset, maxjitter.
    """
    def __init__(self, event_type, period, offset, maxjitter, id=None):
        self.id = id
        self.event_type = event_type  # "read" or "write"
        self.period = period
        self.offset = offset
        self.maxjitter = maxjitter  # J_i in our paper
        self.random_jitter = 0   # jitter of instance

    """print an event"""
    def __repr__(self):
        return (
            f"Event(type={self.event_type},id={self.id}, period={self.period}, "
            f"offset={self.offset}, maxjitter={self.maxjitter}"
        )

    """Generate an instance jitter"""
    def get_trigger_time(self, j):
        self.random_jitter = random.uniform(0, self.maxjitter)
        tj = j * self.period + self.offset + self.random_jitter
        return tj


"""a task"""
class Task:
    """
    Creates a task represented by ID, events, period, offset.
    """
    def __init__(self, read_event, write_event, id=None):
        self.id = id
        self.read_event = read_event
        self.write_event = write_event
        self.period = read_event.period
        self.offset = read_event.offset

    def read_time(self, k):
        return self.read_event.offset + k * self.period
    
    def write_time(self, k):
        return self.write_event.offset + k * self.period

    """print a task"""
    def __repr__(self):
        return (
            f"Task(period={self.period}, offset={self.offset}, "
            f"read_event={self.read_event}, write_event={self.write_event})"
        )


"""
Generate random events
"""
class RandomEvent:
    """
    Generates maximum jitter as percentage per_jitter 
    maxjitter = per_jitter * period
    """
    def __init__(
        self,
        num_tasks,
        periods,
        read_offsets,
        write_offsets,
        per_jitter
    ):
        self.num_tasks = num_tasks
        self.periods = periods
        self.read_offsets = read_offsets
        self.write_offsets = write_offsets
        self.per_jitter = per_jitter
        self.tasks = self.generate_events_tasks()
        
    """
    Generating tasks with events
    """
    def generate_events_tasks(self):
        read_events = []
        write_events = []
        events = []
        tasks = []
        for i in range(self.num_tasks):
            # randomly select a period from the list
            period = self.periods[i]
            read_offset = self.read_offsets[i]
            write_offset = self.write_offsets[i]
            # x% * period
            maxjitter = self.per_jitter*period

            # create read and write events
            read_event = Event(
                event_type="read",
                period=period,
                offset=read_offset,
                maxjitter=maxjitter,
                id=i,
            )
            write_event = Event(
                event_type="write",
                period=period,
                offset=write_offset,
                maxjitter=maxjitter,
                id=i,
            )
            read_events.append(read_event)
            write_events.append(write_event)
            events.append((read_event, write_event))

            # Create a task with the read and write events
            task = Task(read_event=read_event, write_event=write_event, id=i)
            tasks.append(task)

        return tasks

    def get_tasks(self):
        return self.tasks
    

"""Calculate the least common multiple (LCM) of two numbers"""
def lcm(a, b):
    return abs(a * b) // math.gcd(a, b)

"""Calculate the least common multiple of a list of numbers (used to calculate Hyperperiod)"""
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
    """
    Core calculation logic: Calculate the delay of the task chain triggered from time point z.
    Follow zeroLET semantics: the output of the current task's write operation is used as the input of the next task's read operation.
    """
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
    """
    All possible time points z are traversed within a super period H and a delay distribution histogram is generated.
    """
    periods = [task.period for task in tasks]
    H = lcm_list(periods)
    # print(f"Hyperperiod: {H}")

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
