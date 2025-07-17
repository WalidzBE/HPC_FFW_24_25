import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
import numpy as np
import argparse
import re

# Argument parsing
parser = argparse.ArgumentParser(description='Analyze NSYS GPU traces.')
parser.add_argument('--experiment', choices=['basic', 'channel_thread', 'halo'], required=True,
                    help='Experiment name: basic, channel_thread, or halo')
args = parser.parse_args()

# Construct the results directory based on the experiment
results_dir = f'output/performance/{args.experiment}/nsys_profiles/results'

# Get all trace and mem files
trace_files = sorted(glob.glob(os.path.join(results_dir, "*K_block_size*_gputrace.csv")))
mem_files = sorted(glob.glob(os.path.join(results_dir, "*K_block_size*_gpumemsizesum.csv")))

# Hardcoded resolutions and block sizes
resolutions = [4, 8, 16, 32]
all_block_sizes = [4, 8, 16, 32]

# Data storage: {resolution: {block_size: metrics}}
data = {}

for trace_file in trace_files:
    base = os.path.basename(trace_file)
    m = re.match(r"(\d+)K_block_size(\d+)_gputrace\.csv", base)
    if not m:
        continue
    resolution, block_size = int(m.group(1)), int(m.group(2))
    if resolution not in resolutions:
        continue
    mem_file = os.path.join(results_dir, f"{resolution}K_block_size{block_size}_gpumemsizesum.csv")
    if not os.path.exists(mem_file):
        continue

    # Read and process trace file
    trace_df = pd.read_csv(trace_file)
    # Get durations for HtoD, kernel, DtoH
    htod_row = trace_df[trace_df['Name'].str.contains('HtoD', na=False)]
    kernel_row = trace_df[trace_df['Name'].str.contains('applyGaussianBlur', na=False)]
    dtoh_row = trace_df[trace_df['Name'].str.contains('DtoH', na=False)]
    if kernel_row.empty or htod_row.empty or dtoh_row.empty:
        continue

    htod_time = htod_row['Duration (ns)'].values[0] / 1e6
    kernel_time = kernel_row['Duration (ns)'].values[0] / 1e6
    dtoh_time = dtoh_row['Duration (ns)'].values[0] / 1e6

    # Read and process memory file for memory sizes
    mem_df = pd.read_csv(mem_file)
    htod_mem = 0
    dtoh_mem = 0
    op_col = next((col for col in mem_df.columns if "Operation" in col), None)
    size_col = next((col for col in mem_df.columns if "Total" in col), None)
    if op_col and size_col:
        for i, row in mem_df.iterrows():
            op = str(row[op_col])
            size_str = str(row[size_col]).replace('"', '').replace(',', '.')
            try:
                size_val = float(size_str)
            except ValueError:
                size_val = 0
            if "HtoD" in op:
                htod_mem = size_val
            elif "DtoH" in op:
                dtoh_mem = size_val
    else:
        mem_columns = mem_df.columns.tolist()
        name_col = next((col for col in mem_columns if col.lower() == "name"), None)
        size_col = next((col for col in mem_columns if "size" in col.lower()), None)
        if name_col is not None and size_col is not None:
            htod_mem_rows = mem_df[mem_df[name_col].astype(str).str.contains('HtoD', na=False)]
            dtoh_mem_rows = mem_df[mem_df[name_col].astype(str).str.contains('DtoH', na=False)]
            htod_mem = float(htod_mem_rows[size_col].astype(str).str.replace(',', '.').values[0]) if not htod_mem_rows.empty else 0
            dtoh_mem = float(dtoh_mem_rows[size_col].astype(str).str.replace(',', '.').values[0]) if not dtoh_mem_rows.empty else 0

    if resolution not in data:
        data[resolution] = {}
    data[resolution][block_size] = {
        'htod_time': htod_time,
        'kernel_time': kernel_time,
        'dtoh_time': dtoh_time,
        'htod_mem': htod_mem,
        'dtoh_mem': dtoh_mem
    }

# Plotting: create a separate figure for each resolution (only durations)
figs = []
for idx, resolution in enumerate(resolutions):
    fig, ax1 = plt.subplots(1, 1, figsize=(6, 5.5))
    figs.append(fig)
    x = np.arange(len(all_block_sizes))
    bar_width = 0.5

    # Stacked bar for HtoD, kernel, DtoH durations
    htod_times = [data.get(resolution, {}).get(bs, {}).get('htod_time', 0) for bs in all_block_sizes]
    kernel_times = [data.get(resolution, {}).get(bs, {}).get('kernel_time', 0) for bs in all_block_sizes]
    dtoh_times = [data.get(resolution, {}).get(bs, {}).get('dtoh_time', 0) for bs in all_block_sizes]

    ax1.bar(x, htod_times, bar_width, color='tab:green', label='HtoD')
    ax1.bar(x, kernel_times, bar_width, bottom=htod_times, color='tab:blue', label='Kernel')
    ax1.bar(x, dtoh_times, bar_width, bottom=np.array(htod_times)+np.array(kernel_times), color='tab:orange', label='DtoH')
    ax1.set_title(f'HtoD, Kernel, DtoH Durations for {resolution}K', fontsize=14)
    ax1.set_xlabel('Block Size', fontsize=12)
    ax1.set_ylabel('Time (ms)', fontsize=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels([str(bs) for bs in all_block_sizes])
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.legend()

    # Add data labels for stacked bars
    for i in range(len(all_block_sizes)):
        total = htod_times[i]
        if total:
            ax1.text(x[i], total/2, f'{htod_times[i]:.1f}', ha='center', va='center', color='black', fontsize=8)
        total += kernel_times[i]
        if kernel_times[i]:
            ax1.text(x[i], htod_times[i] + kernel_times[i]/2, f'{kernel_times[i]:.1f}', ha='center', va='center', color='white', fontsize=8)
        total += dtoh_times[i]
        if dtoh_times[i]:
            ax1.text(x[i], htod_times[i] + kernel_times[i] + dtoh_times[i]/2, f'{dtoh_times[i]:.1f}', ha='center', va='center', color='black', fontsize=8)

    plt.tight_layout()

# Final graph: compare memory size wrt image size (resolution)
fig_mem, ax_mem = plt.subplots(figsize=(6, 5.5))
mem_x = [f"{r}K" for r in resolutions]
htod_mem_by_res = []
dtoh_mem_by_res = []

for resolution in resolutions:
    # Use the largest block size available for each resolution (or any consistent block size)
    bs_avail = sorted(data.get(resolution, {}).keys())
    if bs_avail:
        bs = bs_avail[-1]
        htod_mem_by_res.append(data[resolution][bs]['htod_mem'])
        dtoh_mem_by_res.append(data[resolution][bs]['dtoh_mem'])
    else:
        htod_mem_by_res.append(0)
        dtoh_mem_by_res.append(0)

bar_width = 0.35
x = np.arange(len(resolutions))
ax_mem.bar(x - bar_width/2, htod_mem_by_res, bar_width, label='HtoD Mem (MB)', color='tab:green', alpha=0.8)
ax_mem.bar(x + bar_width/2, dtoh_mem_by_res, bar_width, label='DtoH Mem (MB)', color='tab:orange', alpha=0.5)
ax_mem.set_title('Memory Transfer Size vs Image Size (Resolution)', fontsize=14)
ax_mem.set_xlabel('Image Size (Resolution)', fontsize=12)
ax_mem.set_ylabel('Size (MB)', fontsize=12)
ax_mem.set_xticks(x)
ax_mem.set_xticklabels(mem_x)
ax_mem.grid(True, linestyle='--', alpha=0.7)
ax_mem.legend()

# Add data labels for memory bars
for i, val in enumerate(htod_mem_by_res):
    if val:
        ax_mem.text(x[i] - bar_width/2, val + 0.05 * val, f'{val:.1f}', ha='center', va='bottom', fontsize=8)
for i, val in enumerate(dtoh_mem_by_res):
    if val:
        ax_mem.text(x[i] + bar_width/2, val + 0.05 * val, f'{val:.1f}', ha='center', va='bottom', fontsize=8)

plt.tight_layout()

plt.show()
