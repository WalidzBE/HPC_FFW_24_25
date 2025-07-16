import re
import matplotlib.pyplot as plt

# === Parametri ===
input_file = "slurm_output_107963.txt"

# === Struttura dati ===
results = {
    0: {},  # Mode 0
    1: {},  # Mode 1
}

# === Regex per catturare i dati ===
pattern = re.compile(r"Mode (\d)  N=\d+  threads=(\d+)  iters=\d+  ([\d\.]+) ms")

# === Parsing ===
with open(input_file, "r") as f:
    for line in f:
        match = pattern.search(line)
        if match:
            mode = int(match.group(1))
            threads = int(match.group(2))
            time_ms = float(match.group(3))
            results.setdefault(mode, {}).setdefault(threads, []).append(time_ms)

# === Calcola medie ===
threads_sorted = sorted(results[0].keys())
avg_mode0 = [sum(results[0][t]) / len(results[0][t]) for t in threads_sorted]
avg_mode1 = [sum(results[1][t]) / len(results[1][t]) for t in threads_sorted]

# === Plot ===
plt.figure(figsize=(12, 7))
#plt.plot(threads_sorted, avg_mode0, marker='o', label="Mode 0")
plt.plot(threads_sorted, avg_mode1, marker='s', label="Mode 1")

# Etichette sui punti
#for t, y in zip(threads_sorted, avg_mode0):
    #plt.text(t, y, f"{y:.0f} ms", fontsize=8, ha='center', va='bottom')

for t, y in zip(threads_sorted, avg_mode1):
    plt.text(t, y, f"{y:.0f} ms", fontsize=8, ha='center', va='bottom')

plt.xlabel("Number of Threads")
plt.ylabel("Average Execution Time (ms)")
plt.title("Heat Diffusion: Average Execution Time vs Threads")
plt.xticks(threads_sorted, threads_sorted)
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()
