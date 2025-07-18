import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load the results.csv file (single image, single algorithm)
df = pd.read_csv("output/performance/pexels_results.csv", header=None, names=["algorithm", "image", "block_size", "time_ms"])

df["block_size"] = df["block_size"].astype(int)

# Group by block size and compute mean and std
grouped = df.groupby("block_size")["time_ms"].agg(['mean', 'std']).reset_index()

# --- Plot Avg Runtime ± Std vs Block Size ---
plt.figure(figsize=(6, 5.5))
plt.errorbar(grouped["block_size"], grouped["mean"], yerr=grouped["std"], fmt='-o', color='tab:blue', capsize=5)
for _, row in grouped.iterrows():
    plt.text(row["block_size"], row["mean"] + 0.02 * row["mean"], f"{row['mean']:.1f}±{row['std']:.1f}", 
             ha='center', color='tab:blue', fontsize=8)
plt.xlabel("Block Size", fontsize=12)
plt.ylabel("Time (ms)", fontsize=12)
plt.title("Avg Runtime ± Std vs Block Size", fontsize=14)
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.show()

# --- Speedup vs Block Size ---
plt.figure(figsize=(7, 6))
min_block_size = grouped["block_size"].min()
T1 = grouped[grouped["block_size"] == min_block_size]["mean"].iloc[0]
grouped["speedup"] = T1 / grouped["mean"]
grouped["speedup_std"] = np.abs(T1 / (grouped["mean"] ** 2)) * grouped["std"]
plt.errorbar(grouped["block_size"], grouped["speedup"], yerr=grouped["speedup_std"], fmt='-o', color='tab:orange', capsize=5)
for _, row in grouped.iterrows():
    plt.text(row["block_size"], row["speedup"], f"{row['speedup']:.2f}±{row['speedup_std']:.2f}", 
             ha='center', va='bottom', fontsize=8, color='tab:orange')
ideal_speedup = grouped["block_size"] / min_block_size
plt.plot(grouped["block_size"], ideal_speedup, 'k--', alpha=0.7, label='Ideal')
plt.xlabel("Block Size", fontsize=12)
plt.ylabel("Speedup (T1/Tp)", fontsize=12)
plt.title("Speedup vs Block Size (Avg ± Std)", fontsize=14)
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend()
plt.tight_layout()
plt.show()
