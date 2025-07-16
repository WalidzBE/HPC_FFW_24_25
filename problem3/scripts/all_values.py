import re
import matplotlib.pyplot as plt

# === Input file ===
input_file = "slurm_output_107963.txt"

# === Dati ===
results = {0: {}, 1: {}}

# === Regex ===
pattern = re.compile(r"Mode (\d)  N=\d+  threads=(\d+)  iters=\d+  ([\d\.]+) ms")

# === Parse ===
with open(input_file, "r") as f:
    for line in f:
        m = pattern.search(line)
        if m:
            mode = int(m.group(1))
            threads = int(m.group(2))
            time = float(m.group(3))
            results.setdefault(mode, {}).setdefault(threads, []).append(time)

# === Liste ordinate ===
threads_sorted = sorted(results[0].keys())

# === Calcola medie ===
avg_mode0 = [sum(results[0][t])/len(results[0][t]) for t in threads_sorted]
avg_mode1 = [sum(results[1][t])/len(results[1][t]) for t in threads_sorted]

# === Plot ===
plt.figure(figsize=(12, 7))

# Mode 0 scatter
for t in threads_sorted:
    y_vals = results[0][t]
    x_vals = [t] * len(y_vals)
    plt.scatter(x_vals, y_vals, color='blue', alpha=0.6, label="Mode 0 Runs" if t == threads_sorted[0] else "")

# Mode 1 scatter
for t in threads_sorted:
    y_vals = results[1][t]
    x_vals = [t] * len(y_vals)
    plt.scatter(x_vals, y_vals, color='red', alpha=0.6, label="Mode 1 Runs" if t == threads_sorted[0] else "")

# Medie come linea
plt.plot(threads_sorted, avg_mode0, marker='o', color='blue', label="Mode 0 Average")
plt.plot(threads_sorted, avg_mode1, marker='s', color='red', label="Mode 1 Average")

plt.xlabel("Number of Threads")
plt.ylabel("Execution Time (ms)")
plt.title("Execution Time vs Threads (All Runs and Averages)")
plt.xticks(threads_sorted, threads_sorted)
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()
