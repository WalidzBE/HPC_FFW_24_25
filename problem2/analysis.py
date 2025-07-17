import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
import numpy as np

# Load the combined results.csv file
df = pd.read_csv("output/performance/results.csv", header=None, names=["algorithm", "image", "block_size", "time_ms"])

# Extract resolution from image filename (e.g., 4K from 4K.jpg)
df["resolution"] = df["image"].str.extract(r"(\d+)K")
df["resolution"] = df["resolution"].astype(int)
df["block_size"] = df["block_size"].astype(int)

# List of unique resolutions and algorithms
resolutions = sorted(df["resolution"].unique())
algorithms = df["algorithm"].unique()
algo_colors = dict(zip(algorithms, plt.cm.tab10.colors[:len(algorithms)]))

figs = []
for res in resolutions:
    fig = plt.figure(figsize=(6, 5.5))
    figs.append(fig)
    df_res = df[df["resolution"] == res]
    for algo in algorithms:
        df_algo = df_res[df_res["algorithm"] == algo]
        # Group by block_size and block_size for mean/std
        grouped = df_algo.groupby(["block_size"])["time_ms"].agg(['mean', 'std']).reset_index()
        plt.errorbar(grouped["block_size"], grouped["mean"], yerr=grouped["std"], fmt='-o',
                     color=algo_colors[algo], capsize=5, label=algo)
        # Add data labels
        for _, row in grouped.iterrows():
            plt.text(row["block_size"], row["mean"] + 0.02 * row["mean"], f"{row['mean']:.1f}", 
                     ha='center', color=algo_colors[algo], fontsize=8)
    plt.xlabel("Block Size", fontsize=12)
    plt.ylabel("Time (ms)", fontsize=12)
    plt.title(f"Runtime vs Block Size ({res}K)", fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(title="Algorithm")
    plt.tight_layout()
    # Do not call plt.show() here

plt.show()
# --- Speedup vs Block Size (all algorithms, all resolutions) ---

for algo in algorithms:
    fig = plt.figure(figsize=(6, 5.5))
    df_algo = df[df["algorithm"] == algo]
    block_sizes = sorted(df_algo["block_size"].unique())
    colors = plt.cm.tab10.colors  # Use tab10 colormap for distinct lines
    for idx, res in enumerate(resolutions):
        df_res = df_algo[df_algo["resolution"] == res]
        if df_res.empty:
            continue
        min_block_size = df_res["block_size"].min()
        T1 = df_res[df_res["block_size"] == min_block_size]["time_ms"].iloc[0]
        df_res = df_res.copy()
        df_res["speedup"] = T1 / df_res["time_ms"]
        color = colors[idx % len(colors)]
        plt.plot(df_res["block_size"], df_res["speedup"], '-o',
                 label=f"{algo} {res}K", color=color)
        # Add data labels
        for _, row in df_res.iterrows():
            plt.text(row["block_size"], row["speedup"], f"{row['speedup']:.2f}", 
                     ha='center', va='bottom', fontsize=8, color=color)
        # Ideal speedup line: ideal = block_size / min_block_size
        ideal_speedup = df_res["block_size"] / min_block_size
        plt.plot(df_res["block_size"], ideal_speedup, 'k--', alpha=0.7, label=f'Ideal {res}K' if idx == 0 else None)

    plt.xlabel("Block Size", fontsize=12)
    plt.ylabel("Speedup (T1/Tp)", fontsize=12)
    plt.title(f"Speedup vs Block Size ({algo})", fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(title="Resolution")
    plt.tight_layout()
    plt.show()
