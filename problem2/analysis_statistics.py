import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load the combined results.csv file (with multiple runs)
df = pd.read_csv("output/performance/stats_results.csv", header=None, names=["algorithm", "image", "block_size", "time_ms"])

# Only use CHANNEL_THREAD algorithm
df = df[df["algorithm"] == "CHANNEL_THREAD"]

# Extract resolution from image filename (e.g., 4K from 4K.jpg)
df["resolution"] = df["image"].str.extract(r"(\d+)K")
df["resolution"] = df["resolution"].astype(int)
df["block_size"] = df["block_size"].astype(int)

# List of unique resolutions
resolutions = sorted(df["resolution"].unique())
algo_color = 'tab:blue'

# Plot average and stddev of runtime vs block size for each resolution
for res in resolutions:
    fig = plt.figure(figsize=(6, 5.5))
    df_res = df[df["resolution"] == res]
    grouped = df_res.groupby("block_size")["time_ms"].agg(['mean', 'std']).reset_index()
    plt.errorbar(grouped["block_size"], grouped["mean"], yerr=grouped["std"], fmt='-o',
                 color=algo_color, capsize=5, label="CHANNEL_THREAD")
    for _, row in grouped.iterrows():
        plt.text(row["block_size"], row["mean"] + 0.02 * row["mean"], f"{row['mean']:.1f}±{row['std']:.1f}", 
                 ha='center', color=algo_color, fontsize=8)
    plt.xlabel("Block Size", fontsize=12)
    plt.ylabel("Time (ms)", fontsize=12)
    plt.title(f"Avg Runtime ± Std vs Block Size ({res}K)", fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.tight_layout()
    # Do not call plt.show() here

plt.show()

# --- Speedup vs Block Size (CHANNEL_THREAD, avg ± std) ---

fig = plt.figure(figsize=(7, 6))
colors = plt.cm.tab10.colors  # Use tab10 colormap for distinct lines
for idx, res in enumerate(resolutions):
    df_res = df[df["resolution"] == res]
    grouped = df_res.groupby("block_size")["time_ms"].agg(['mean', 'std']).reset_index()
    min_block_size = grouped["block_size"].min()
    T1 = grouped[grouped["block_size"] == min_block_size]["mean"].iloc[0]
    grouped["speedup"] = T1 / grouped["mean"]
    grouped["speedup_std"] = np.abs(T1 / (grouped["mean"] ** 2)) * grouped["std"]
    color = colors[idx % len(colors)]
    plt.errorbar(grouped["block_size"], grouped["speedup"], yerr=grouped["speedup_std"], fmt='-o',
                 color=color, capsize=5, label=f"{res}K")
    for _, row in grouped.iterrows():
        plt.text(row["block_size"], row["speedup"], f"{row['speedup']:.2f}±{row['speedup_std']:.2f}", 
                 ha='center', va='bottom', fontsize=8, color=color)
    ideal_speedup = grouped["block_size"] / min_block_size
    plt.plot(grouped["block_size"], ideal_speedup, 'k--', alpha=0.7, label=f'Ideal {res}K' if idx == 0 else None)

plt.xlabel("Block Size", fontsize=12)
plt.ylabel("Speedup (T1/Tp)", fontsize=12)
plt.title("Speedup vs Block Size (CHANNEL_THREAD, Avg ± Std)", fontsize=14)
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend(title="Resolution")
plt.tight_layout()
plt.show()
