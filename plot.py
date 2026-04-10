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
import ast
import os
import matplotlib.pyplot as plt
import csv
import numpy as np
import argparse 
import pandas as pd
from matplotlib.gridspec import GridSpec


def plot_R_histogram_our(csv_file,R_plot_name,tag='passive'):
    """
    Read csv_file, retain only the data with per_jitter = 20%,
    group by num_tasks, plot an R value histogram (50 bins evenly spaced from 0 to 1.05),
    and calculate the proportion of R values greater than 1.
    R = DFFbase/DFFbound in our paper.

    arguments:
        csv_file: The CSV file containing the data
        R_plot_name: The name of the output plot file
        tag: A tag to include in the plot title (default is 'passive')
    return:
        None

    """
    num_tasks_to_r_values = {}
    r_exceed_count = 0  # Counter for R values exceeding 1.0
    total_rows = 0 
    TOLERANCE = 1e-9
    with open(csv_file, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            total_rows += 1 
            per_jitter = float(row['per_jitter'])
            r_value = float(row['R']) if row['R'] else None
            num_tasks = int(row['num_tasks'])

            if per_jitter == 0.2 and r_value is not None:  # Only consider per_jitter = 20%
                if num_tasks not in num_tasks_to_r_values:
                    num_tasks_to_r_values[num_tasks] = []
                num_tasks_to_r_values[num_tasks].append(r_value)
                if r_value > 1 + TOLERANCE:
                    print(f"Warning: R value {r_value} exceeds 1.0 for per_jitter={per_jitter}. This may indicate an error in the data.")
                    r_exceed_count += 1  

    if total_rows == 0:
        print("No data found.")
        return
                
    R_exceed_percentage = r_exceed_count / total_rows * 100 if total_rows > 0 else 0

    num_num_tasks = len(num_tasks_to_r_values)
    if num_num_tasks == 0:
        print("No valid data found for the specified conditions.")
        return

    num_columns = 2  
    num_rows = (num_num_tasks + num_columns - 1) // num_columns

    fig, axes = plt.subplots(num_rows, num_columns, figsize=(15, 5 * num_rows))
    axes = axes.flatten()

    colors = plt.cm.tab10(np.linspace(0, 1, num_num_tasks))  

    for idx, (num_tasks, r_values) in enumerate(num_tasks_to_r_values.items()):
        ax = axes[idx]
        num_bins = 50
        bin_range = (0, 1.05)
        bin_width = (bin_range[1] - bin_range[0]) / num_bins

        counts, bin_edges = np.histogram(r_values, bins=num_bins, range=bin_range)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        ax.bar(bin_centers, counts, width=bin_width, alpha=0.7, align='center', color=colors[idx], label=f'num_tasks={num_tasks}')

        r_values_greater_than_1 = len([r for r in r_values if r > 1])
        percentage_greater_than_1 = (r_values_greater_than_1 / len(r_values)) * 100 if len(r_values) > 0 else 0

        ax.set_title(f"num_tasks = {num_tasks} - our ({tag}) - Data Count: {len(r_values)}")
        ax.set_xlabel(f"R_exceed_percentage = {percentage_greater_than_1:.2f}%")
        ax.set_ylabel("Frequency")
        ax.legend()
        ax.grid(True)

    for idx in range(num_num_tasks, num_rows * num_columns):
        axes[idx].axis('off')

    plt.tight_layout()
    plt.suptitle(f"Distribution of R values for different num_tasks (per_jitter=20%),R_exceed_percentage={R_exceed_percentage}", fontsize=16, y=1.05)

    plt.savefig(R_plot_name)



def plot_R_histogram_LET(csv_file,R_plot_name_LET,tag='passive'):
    """
    No filtering per_jitter required
    R = DFF_Gunzel_LET/DFFbound in our paper.
    arguments:
        csv_file: The CSV file containing the data
        R_plot_name_LET: The name of the output plot file
        tag: A tag to include in the plot title (default is 'passive')
    return:
        None
    """
    num_tasks_to_r_values = {}
    r_exceed_count = 0  # Counter for R values exceeding 1.0
    total_rows = 0 
    TOLERANCE = 1e-9
    with open(csv_file, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            total_rows += 1 
            r_value = float(row['R']) if row['R'] else None
            num_tasks = int(row['num_tasks'])

            if r_value is not None:  
                if num_tasks not in num_tasks_to_r_values:
                    num_tasks_to_r_values[num_tasks] = []
                num_tasks_to_r_values[num_tasks].append(r_value)
                if r_value > 1 + TOLERANCE:
                    print(f"Warning: R value {r_value} exceeds 1.0. This may indicate an error in the data.")
                    r_exceed_count += 1  

    if total_rows == 0:
        print("No data found.")
        return
                
    R_exceed_percentage = r_exceed_count / total_rows * 100 if total_rows > 0 else 0

    num_num_tasks = len(num_tasks_to_r_values)
    if num_num_tasks == 0:
        print("No valid data found for the specified conditions.")
        return

    num_columns = 2  
    num_rows = (num_num_tasks + num_columns - 1) // num_columns

    fig, axes = plt.subplots(num_rows, num_columns, figsize=(15, 5 * num_rows))
    axes = axes.flatten()

    colors = plt.cm.tab10(np.linspace(0, 1, num_num_tasks))  

    for idx, (num_tasks, r_values) in enumerate(num_tasks_to_r_values.items()):
        ax = axes[idx]
        num_bins = 50
        bin_range = (0, 1.05)
        bin_width = (bin_range[1] - bin_range[0]) / num_bins

        counts, bin_edges = np.histogram(r_values, bins=num_bins, range=bin_range)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        ax.bar(bin_centers, counts, width=bin_width, alpha=0.7, align='center', color=colors[idx], label=f'num_tasks={num_tasks}')

        r_values_greater_than_1 = len([r for r in r_values if r > 1])
        percentage_greater_than_1 = (r_values_greater_than_1 / len(r_values)) * 100 if len(r_values) > 0 else 0

        ax.set_title(f"num_tasks = {num_tasks} - LET ({tag}) - Data Count: {len(r_values)}")
        ax.set_xlabel(f"R_exceed_percentage = {percentage_greater_than_1:.2f}%")
        ax.set_ylabel("Frequency")
        ax.legend()
        ax.grid(True)

    for idx in range(num_num_tasks, num_rows * num_columns):
        axes[idx].axis('off')

    plt.tight_layout()
    plt.suptitle(f"Distribution of R values for different num_tasks (LET),R_exceed_percentage={R_exceed_percentage}", fontsize=16, y=1.05)


    plt.savefig(R_plot_name_LET)



def plot_R_histogram_IC(csv_file,R_plot_name_IC,tag='passive'):
    """
    No filtering per_jitter required
    R = DFF_Gunzel_IC/DFFbound in our paper.
    arguments:
        csv_file: The CSV file containing the data
        R_plot_name_IC: The name of the output plot file
        tag: A tag to include in the plot title (default is 'passive')
    return:
        None
    """
    num_tasks_to_r_values = {}
    r_exceed_count = 0  # Counter for R values exceeding 1.0
    total_rows = 0 
    TOLERANCE = 1e-9
    with open(csv_file, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            total_rows += 1 
            r_value = float(row['R']) if row['R'] else None
            num_tasks = int(row['num_tasks'])

            if r_value is not None:
                if num_tasks not in num_tasks_to_r_values:
                    num_tasks_to_r_values[num_tasks] = []
                num_tasks_to_r_values[num_tasks].append(r_value)
                if r_value > 1 + TOLERANCE:
                    print(f"Warning: R value {r_value} exceeds 1.0 . This may indicate an error in the data.")
                    r_exceed_count += 1  

    if total_rows == 0:
        print("No data found.")
        return
                
    R_exceed_percentage = r_exceed_count / total_rows * 100 if total_rows > 0 else 0

    num_num_tasks = len(num_tasks_to_r_values)
    if num_num_tasks == 0:
        print("No valid data found for the specified conditions.")
        return

    num_columns = 2  
    num_rows = (num_num_tasks + num_columns - 1) // num_columns

    fig, axes = plt.subplots(num_rows, num_columns, figsize=(15, 5 * num_rows))
    axes = axes.flatten()

    colors = plt.cm.tab10(np.linspace(0, 1, num_num_tasks))  

    for idx, (num_tasks, r_values) in enumerate(num_tasks_to_r_values.items()):
        ax = axes[idx]
        num_bins = 50
        bin_range = (0, 1.05)
        bin_width = (bin_range[1] - bin_range[0]) / num_bins

        counts, bin_edges = np.histogram(r_values, bins=num_bins, range=bin_range)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        ax.bar(bin_centers, counts, width=bin_width, alpha=0.7, align='center', color=colors[idx], label=f'num_tasks={num_tasks}')

        r_values_greater_than_1 = len([r for r in r_values if r > 1])
        percentage_greater_than_1 = (r_values_greater_than_1 / len(r_values)) * 100 if len(r_values) > 0 else 0

        ax.set_title(f"num_tasks = {num_tasks} - IC ({tag}) - Data Count: {len(r_values)}")
        ax.set_xlabel(f"R_exceed_percentage = {percentage_greater_than_1:.2f}%")
        ax.set_ylabel("Frequency")
        ax.legend()
        ax.grid(True)

    for idx in range(num_num_tasks, num_rows * num_columns):
        axes[idx].axis('off')

    plt.tight_layout()
    plt.suptitle(f"Distribution of R values for different num_tasks (IC),R_exceed_percentage={R_exceed_percentage}", fontsize=16, y=1.05)

    plt.savefig(R_plot_name_IC)



def plot_runtime(csv_path, runtime_name, tag='passive'):
    """
    Read csv, group by num_tasks, and calculate the average of run_time_G (Gunzel) and run_time_our (our).
    arguments:
        csv_path: The path to the CSV file containing the data
        runtime_name: The name of the output plot file
        tag: A tag to include in the plot title (default is 'passive')
    return:
        None
    """
    df = pd.read_csv(csv_path)

    avg = (df
            .groupby('num_tasks')[['run_time_G', 'run_time_our']]
            .mean()
            .reset_index()
            .sort_values('num_tasks'))
    plt.figure(figsize=(6, 4))
    plt.plot(avg['num_tasks'], avg['run_time_G'],
                marker='o', label='run_time_G (Average)')
    plt.plot(avg['num_tasks'], avg['run_time_our'],
                marker='^', label='run_time_our (Average)')
    plt.yscale('log')
    plt.xlabel('num_tasks')
    plt.ylabel('Average Runtime (s)')
    plt.title(f' Average Runtime vs. num_tasks ({tag})')

    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()

    plt.savefig(runtime_name, dpi=300)



def plot_false_percent(csv_file, percent_plot_name, tag='passive'):
    """
    Group by num_tasks and plot a line with false_percentage varying with jitter.
    arguments:
        csv_file: The CSV file containing the data
        percent_plot_name: The name of the output plot file
        tag: A tag to include in the plot title (default is 'passive')
    return:
        None
    """
    jitter_to_false_percentage = {}
    with open(csv_file, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            per_jitter = float(row['per_jitter'])
            false_percentage = float(row['false_percentage'])  
            num_tasks = int(row['num_tasks'])  

            if num_tasks not in jitter_to_false_percentage:
                jitter_to_false_percentage[num_tasks] = {}

            if per_jitter not in jitter_to_false_percentage[num_tasks]:
                jitter_to_false_percentage[num_tasks][per_jitter] = []

            jitter_to_false_percentage[num_tasks][per_jitter].append(false_percentage)

    plt.figure(figsize=(10, 6))
    for num_tasks, jitter_data in jitter_to_false_percentage.items():
        jitter_percent = [jitter * 100 for jitter in sorted(jitter_data.keys())]
        false_percentages = [np.mean(jitter_data[jitter]) * 100 for jitter in sorted(jitter_data.keys())]
        plt.plot(jitter_percent, false_percentages, label=f"num_tasks={num_tasks}", marker='o')

    plt.title(f"False Percentage vs. Jitter ({tag})")
    plt.xlabel("Jitter Percentage (%)")
    plt.ylabel("False Percentage (%)")
    plt.legend()
    plt.grid(True)
    plt.xticks(jitter_percent)  
    plt.savefig(f"{percent_plot_name}")



def compare_plot_histogram_our(csv_files, compare_histogram_our_name, mode='default'):
    """
    Comparing two experiments in our paper,
    csv_files (passive and active),
    each with per_jitter = 20% data, plotting histograms side by side by num_tasks.
    arguments:
        csv_files: List of CSV files to be compared
        compare_histogram_our_name: The name of the output plot file
    return:
        None
    """
    dfs = [pd.read_csv(file) for file in csv_files]

    dfs = [df[df['per_jitter'] == 0.2] for df in dfs]

    num_tasks_list = sorted(set.union(*[set(df['num_tasks'].unique()) for df in dfs]))

    fig = plt.figure(figsize=(20, 10 * len(num_tasks_list)))
    outer_grid = GridSpec(len(num_tasks_list), len(csv_files), wspace=0.4, hspace=0.4)

    if mode == '_PAORDER':
        LABELS = ['passive', 'order']
    elif mode == '_ADD':
        LABELS = ['active', 'add']
    else:
        LABELS = ['passive', 'active']
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(num_tasks_list)))
    TOLERANCE = 1e-9
    for idx, num_tasks in enumerate(num_tasks_list):
        for file_idx, df in enumerate(dfs):
            ax = fig.add_subplot(outer_grid[idx, file_idx])
            df_task = df[df['num_tasks'] == num_tasks]

            r_values = df_task['R'].dropna().values
            r_exceed_count = (r_values > (1 + TOLERANCE)).sum()
            R_exceed_percentage = (r_exceed_count / len(r_values)) * 100 if len(r_values) > 0 else 0

            num_bins = 50
            bin_range = (0, 1.05)
            bin_width = (bin_range[1] - bin_range[0]) / num_bins

            counts, bin_edges = np.histogram(r_values, bins=num_bins, range=bin_range)
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            ax.bar(bin_centers, counts, width=bin_width, alpha=0.7, align='center', color=colors[idx], label=f'num_tasks={num_tasks}')

            label = LABELS[file_idx] 
            ax.set_title(f"num_tasks = {num_tasks}  (per_jitter=20%) - our({label}) - Data Count: {len(r_values)}")
            ax.set_xlabel("R_exceed_percentage = {:.2f}%".format(R_exceed_percentage))
            ax.set_ylabel("Frequency")
            ax.legend()
            ax.grid(True)

    plt.savefig(compare_histogram_our_name)



def compare_false_percent_our(csv_files, compare_plot_name, mode='default'):
    """
    Comparing the two experiments in our paper,
    csv_files (passive and active),
    draw a line graph showing the False Percentage as Jitter changes.
    arguments:
        csv_files: List of CSV files to be compared
        compare_plot_name: The name of the output plot file     
    return:
        None
    """
    num_csv_files = len(csv_files)
    num_columns = 2
    num_rows = (num_csv_files + num_columns - 1) // num_columns

    fig, axes = plt.subplots(num_rows, num_columns, figsize=(15, 5 * num_rows))
    axes = axes.flatten()

    if mode == '_PAORDER':
        LABELS = ['passive', 'order']
    elif mode == '_ADD':
        LABELS = ['active', 'add']
    else:
        LABELS = ['passive', 'active']

    for idx, csv_file in enumerate(csv_files):
        ax = axes[idx]
        try:
            df = pd.read_csv(csv_file)
        except FileNotFoundError:
            print(f"File not found: {csv_file}")
            continue
        except pd.errors.EmptyDataError:
            print(f"No data in CSV file: {csv_file}")
            continue

        label = LABELS[idx] 
        
        grouped_by_num_tasks = df.groupby('num_tasks')

        for num_tasks, group in grouped_by_num_tasks:
            group_sorted = group.sort_values(by='per_jitter')

            per_jitters = group_sorted['per_jitter'] * 100
            false_percentages = group_sorted['finalpercent']

            ax.plot(per_jitters, false_percentages, label=f'num_tasks={num_tasks}', marker='o')

        ax.set_title(f"False Percentage vs. Jitter ({label})")
        ax.set_xlabel("Jitter Percentage (%)")
        ax.set_ylabel("False Percentage (%)")
        ax.legend()
        ax.grid(True)
    
    for idx in range(num_csv_files, num_rows * num_columns):
        axes[idx].axis('off')
    
    y_min = min(ax.get_ylim()[0] for ax in axes if ax.has_data())
    y_max = max(ax.get_ylim()[1] for ax in axes if ax.has_data())
    for ax in axes:
        ax.set_ylim(y_min, y_max)

    plt.tight_layout()
    plt.savefig(compare_plot_name)



def plot_false_percent_order_old(order_file_name, csv_file):
    # Load data from CSV
    df = pd.read_csv(csv_file)
    
    # Extract unique values
    chain_types = df['chain_type'].unique()
    num_tasks_values = df['num_tasks'].unique()
    per_jitter_values = df['per_jitter'].unique()

    fig, axs = plt.subplots(1, len(chain_types), figsize=(15, 5), sharey=True)

    for i, chain_type in enumerate(chain_types):
        ax = axs[i]
        for num_tasks in num_tasks_values:
            subset = df[(df['chain_type'] == chain_type) & (df['num_tasks'] == num_tasks)]
            subset = subset.sort_values(by='per_jitter')
            ax.plot(subset['per_jitter'], subset['false_percentage_by_num_tasks'], marker='o', label=f'num_tasks={num_tasks}')
        
        ax.set_title(f'Failure Rates for {chain_type}')
        ax.set_xlabel('Jitter')
        ax.set_ylabel('Failure Rate')
        ax.legend()
        ax.grid(True)
    
    plt.tight_layout()
    plt.savefig(order_file_name)
    print(f"Plot generated and saved to {order_file_name}")
    # plt.close()

def plot_type_percent_order_old(type_order_file_name, csv_file):
    # Load data from CSV
    df = pd.read_csv(csv_file)
    
    # Extract unique values
    chain_types = df['chain_type'].unique()
    num_tasks_values = df['num_tasks'].unique()
    per_jitter_values = df['per_jitter'].unique()
    
    fig, axs = plt.subplots(1, len(num_tasks_values), figsize=(15, 5), sharey=True)

    if len(num_tasks_values) == 1:
        axs = [axs]  # 如果只有一个子图，确保 axs 是可迭代的
    
    for i, num_tasks in enumerate(num_tasks_values):
        ax = axs[i]
        for chain_type in chain_types:
            subset = df[(df['num_tasks'] == num_tasks) & (df['chain_type'] == chain_type)]
            subset = subset.sort_values(by='per_jitter')
            ax.plot(subset['per_jitter'], subset['false_percentage_by_chain_type'], marker='o', label=f'chain_type={chain_type}')
        
        ax.set_title(f'Failure Rates for num_tasks={num_tasks}')
        ax.set_xlabel('Jitter')
        ax.set_ylabel('Failure Rate')
        ax.legend()
        ax.grid(True)
    
    plt.tight_layout()
    plt.savefig(type_order_file_name)
    print(f"Plot generated and saved to {type_order_file_name}")
    # plt.close()

def plot_R_histogram_our_order_old(order_r_plot_name, csv_file):
    # Load data from CSV
    df = pd.read_csv(csv_file)

    # Convert R column to numeric, forcing errors to NaN
    df['R'] = pd.to_numeric(df['R'], errors='coerce')

    # Extract unique values
    chain_types = df['chain_type'].unique()
    num_tasks_values = df['num_tasks'].unique()
    per_jitter_values = df['per_jitter'].unique()
    TOLERANCE = 1e-9
    # Create subplots
    fig, axs = plt.subplots(len(num_tasks_values), len(chain_types), figsize=(20, 10), sharey=True)
    
    # Define colors for different per_jitter values
    colors = plt.cm.viridis(np.linspace(0, 1, len(per_jitter_values)))
    handles = []
    labels = []
    for i, num_tasks in enumerate(num_tasks_values):
        for j, chain_type in enumerate(chain_types):
            ax = axs[i, j]
            r_values_all_jitter = []
            for k, per_jitter in enumerate(per_jitter_values):
                subset = df[(df['chain_type'] == chain_type) & (df['num_tasks'] == num_tasks) & (df['per_jitter'] == per_jitter)]
                r_values = subset['R'].dropna()
                # r_values = subset['R'].dropna().to_numpy(dtype=float)
                # r_values_all_jitter = np.array(r_values_all_jitter, dtype=float)
                r_values_all_jitter.extend(r_values)
                # Plot histogram for each per_jitter with different color
                hist = ax.hist(r_values, bins=20, alpha=0.5, color=colors[k])
                
                # Only add the first handle for each per_jitter to the legend
                if i == 0 and j == 0:
                    handles.append(hist[-1][0])
                    labels.append(f'per_jitter={per_jitter}')

                # # Plot histogram for each per_jitter with different color
                # ax.hist(r_values, bins=20, alpha=0.5, color=colors[k], label=f'per_jitter={per_jitter}')
            
            # Calculate the total number of samples
            total_samples = len(r_values_all_jitter)
            
            # Calculate the number of samples where R > 1
            r_exceed_count = 0
            for r in r_values_all_jitter:
                if r > 1 + TOLERANCE:
                    r_exceed_count += 1
                    print(f"Warning: R value {r} exceeds 1.0 for num_tasks={num_tasks}, chain_type={chain_type}, per_jitter={per_jitter}. This may indicate an error in the data.")
            # Calculate the percentage of R values greater than 1
            if total_samples > 0:
                r_exceed_percentage = (r_exceed_count / total_samples) * 100
            else:
                r_exceed_percentage = 0.0

            # Set title with the percentage of R values greater than 1 and total sample count
            ax.set_title(f'num_tasks={num_tasks}, {chain_type}, - Data Count: {total_samples}')
            ax.set_xlabel(f'R Value, R_exceed_percentage = {r_exceed_percentage:.2f}%')
            ax.set_ylabel('Frequency')
            # ax.legend()
            ax.grid(True)

    plt.legend(handles, labels, loc='upper right', bbox_to_anchor=(1.1, 1.05), title="Legend", fontsize=8)

    plt.tight_layout()
    plt.savefig(order_r_plot_name)
    print(f"Plot generated and saved to {order_r_plot_name}")
    

    

def parse_list_string(s):
    """Safely convert string like '[1,2,3,4]' to list of floats."""
    try:
        return [float(x) for x in ast.literal_eval(s)]
    except (ValueError, SyntaxError):
        return [None, None, None, None]


def _plot_non_overlapping_hist(data_dict, labels, colors, title, xlabel, output_path, add_vline=False):

    plt.figure(figsize=(9, 5))
    
    # 合并所有数据以确定全局 bins
    all_vals = []
    for label in labels:
        all_vals.extend(data_dict[label])
    if not all_vals:
        raise ValueError("No valid data to plot.")
    
    bins = np.linspace(min(all_vals), max(all_vals), 31)  # 30 bins
    bin_width = bins[1] - bins[0]
    offset_step = bin_width / (len(labels) + 1)  

    for i, label in enumerate(labels):
        offset = (i - len(labels)/2 + 0.5) * offset_step
        counts, _ = np.histogram(data_dict[label], bins=bins)
        bin_centers = bins[:-1] + bin_width / 2 + offset
        plt.bar(
            bin_centers,
            counts,
            width=offset_step * 0.9,
            color=colors[label],
            label=label,
            alpha=0.8
        )

    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("Frequency")
    # 将图例放在图像外右侧
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
    plt.grid(True, linestyle='--', alpha=0.5)
    if add_vline:
        plt.axvline(0, color='black', linestyle='-', linewidth=1, alpha=0.7)
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()



def plot_sync_original_hist(csv_file, sync_original_plot_name):
    
    labels = ['LF', 'FF', 'LL', 'FL']
    colors = {'LF': 'tab:blue', 'FF': 'tab:orange', 'LL': 'tab:green', 'FL': 'tab:red'}

    df = pd.read_csv(csv_file)
    df['orig'] = df["sync_original"].apply(parse_list_string)

    # Initialize data containers
    orig_data = {label: [] for label in labels}

    for _, row in df.iterrows():
        for i, label in enumerate(labels):
            if row['orig'][i] is not None:
                orig_data[label].append(row['orig'][i])

    _plot_non_overlapping_hist(
        orig_data,
        labels,
        colors,
        title="Histogram of sync_original Latencies",
        xlabel="Latency",
        output_path=sync_original_plot_name,
        add_vline=False
    )




def plot_sync_zero_jitter_hist(csv_file, sync_zero_jitter_plot_name):

    labels = ['LF', 'FF', 'LL', 'FL']
    colors = {'LF': 'tab:blue', 'FF': 'tab:orange', 'LL': 'tab:green', 'FL': 'tab:red'}

    df = pd.read_csv(csv_file)
    df['zj']   = df["sync_zero_jitter"].apply(parse_list_string)

    # Initialize data containers
    zj_data   = {label: [] for label in labels}

    for _, row in df.iterrows():
        for i, label in enumerate(labels):
            if row['zj'][i] is not None:
                zj_data[label].append(row['zj'][i])

    _plot_non_overlapping_hist(
        zj_data,
        labels,
        colors,
        title="Histogram of sync_zero_jitter Latencies",
        xlabel="Latency",
        output_path=sync_zero_jitter_plot_name,
        add_vline=False
    )





def plot_sync_diff_hist(csv_file, diff_sync_plot_name):

    labels = ['LF', 'FF', 'LL', 'FL']
    colors = {'LF': 'tab:blue', 'FF': 'tab:orange', 'LL': 'tab:green', 'FL': 'tab:red'}

    df = pd.read_csv(csv_file)
    df['diff'] = df["diff_sync"].apply(parse_list_string)

    # Initialize data containers
    diff_data = {label: [] for label in labels}

    for _, row in df.iterrows():
        for i, label in enumerate(labels):
            if row['diff'][i] is not None:
                diff_data[label].append(row['diff'][i])

    _plot_non_overlapping_hist(
        diff_data,
        labels,
        colors,
        title="Histogram of diff_sync (Zero-Jitter - Original)",
        xlabel="Δ Latency",
        output_path=diff_sync_plot_name,
        add_vline=True
    )



def plot_combined_latency_histograms(csv_file, sync_plot_name):
    labels = ['LF', 'FF', 'LL', 'FL']
    colors = {'LF': 'tab:blue', 'FF': 'tab:orange', 'LL': 'tab:green', 'FL': 'tab:red'}

    df = pd.read_csv(csv_file)
    df['orig'] = df["sync_original"].apply(parse_list_string)
    df['zj']   = df["sync_zero_jitter"].apply(parse_list_string)
    df['diff'] = df["diff_sync"].apply(parse_list_string)

    orig_data = {label: [] for label in labels}
    zj_data   = {label: [] for label in labels}
    diff_data = {label: [] for label in labels}

    for _, row in df.iterrows():
        for i, label in enumerate(labels):
            if row['orig'][i] is not None:
                orig_data[label].append(row['orig'][i])
            if row['zj'][i] is not None:
                zj_data[label].append(row['zj'][i])
            if row['diff'][i] is not None:
                diff_data[label].append(row['diff'][i])

    fig, axs = plt.subplots(1, 3, figsize=(20, 6), sharey=False)

    datasets = [orig_data, zj_data, diff_data]
    titles = [
        "sync_original",
        "sync_zero_jitter",
        "diff_sync (Zero-Jitter - Original)"
    ]
    xlabels = ["Latency", "Latency", "Δ Latency"]
    add_vlines = [False, False, True]

    for ax, data, title, xlabel, vline in zip(axs, datasets, titles, xlabels, add_vlines):
        # 合并数据确定 bins
        all_vals = [val for label in labels for val in data[label]]
        if not all_vals:
            continue
        bins = np.linspace(min(all_vals), max(all_vals), 31)
        bin_width = bins[1] - bins[0]
        offset_step = bin_width / (len(labels) + 1)

        for i, label in enumerate(labels):
            offset = (i - len(labels)/2 + 0.5) * offset_step
            counts, _ = np.histogram(data[label], bins=bins)
            bin_centers = bins[:-1] + bin_width / 2 + offset
            ax.bar(
                bin_centers,
                counts,
                width=offset_step * 0.9,
                color=colors[label],
                label=label,
                alpha=0.8
            )
        ax.set_title(title, fontsize=11)
        ax.set_xlabel(xlabel, fontsize=10)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend()
        if vline:
            ax.axvline(0, color='black', linestyle='-', linewidth=1, alpha=0.7)

    axs[0].set_ylabel("Frequency", fontsize=10)
    plt.tight_layout(pad=2.0)
    os.makedirs(os.path.dirname(sync_plot_name), exist_ok=True)
    plt.savefig(sync_plot_name, dpi=300, bbox_inches='tight')
    plt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot histograms from a CSV file.")
    # parser.add_argument("csv_file", type=str, help="Path to the CSV file containing the data.")
    parser.add_argument("csv_files", type=str, nargs='+', help="Paths to the CSV files containing the data.")
    parser.add_argument("name", type=str)
    parser.add_argument("--mode", type=str, default='default', help="Mode for comparison (default, PAORDER, ADD).")
    args = parser.parse_args()

    compare_plot_histogram_our(args.csv_files, args.name)
    compare_false_percent_our(args.csv_files, args.name, mode=args.mode)