import re
import matplotlib.pyplot as plt

# === FILES ===
file_1024 = "slurm_output_107963.txt"
file_2048 = "slurm_output_109344_2048.txt"
file_4096 = "slurm_output_116455_4096.txt"  

pattern = re.compile(r"Mode 0\s+N=\d+\s+threads=(\d+)\s+iters=\d+\s+([\d\.]+) ms")

def parse_file(filename):
    results = {}
    with open(filename) as f:
        for line in f:
            m = pattern.search(line)
            if m:
                t = int(m.group(1))
                time = float(m.group(2))
                results.setdefault(t, []).append(time)
    return results

res_1024 = parse_file(file_1024)
res_2048 = parse_file(file_2048)
res_4096 = parse_file(file_4096)

# Assumo che i thread siano gli stessi per tutti i file
threads = sorted(res_1024.keys())

# === Medie ===
avg_1024 = [sum(res_1024[t])/len(res_1024[t]) for t in threads]
avg_2048 = [sum(res_2048[t])/len(res_2048[t]) for t in threads]
avg_4096 = [sum(res_4096[t])/len(res_4096[t]) for t in threads]

T1_1024 = avg_1024[0]
T1_2048 = avg_2048[0]
T1_4096 = avg_4096[0]

speedup_1024 = [T1_1024/t for t in avg_1024]
speedup_2048 = [T1_2048/t for t in avg_2048]
speedup_4096 = [T1_4096/t for t in avg_4096]

eff_1024 = [s/p for s,p in zip(speedup_1024, threads)]
eff_2048 = [s/p for s,p in zip(speedup_2048, threads)]
eff_4096 = [s/p for s,p in zip(speedup_4096, threads)]

# === PLOT SPEEDUP ===
plt.figure(figsize=(12,6))
plt.plot(threads, speedup_1024, marker='o', label="N=1024")
plt.plot(threads, speedup_2048, marker='s', label="N=2048")
plt.plot(threads, speedup_4096, marker='^', label="N=4096")
plt.plot(threads, threads, '--', color='grey', label="Ideal")

for t,s in zip(threads, speedup_1024):
    plt.text(t, s, f"{s:.1f}", fontsize=7, ha='center')
for t,s in zip(threads, speedup_2048):
    plt.text(t, s, f"{s:.1f}", fontsize=7, ha='center')
for t,s in zip(threads, speedup_4096):
    plt.text(t, s, f"{s:.1f}", fontsize=7, ha='center')

plt.title("Speedup vs Threads")
plt.xlabel("Threads")
plt.ylabel("Speedup (T1/Tp)")
plt.xticks(threads)
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

# === PLOT EFFICIENCY ===
plt.figure(figsize=(12,6))
plt.plot(threads, eff_1024, marker='o', label="N=1024")
plt.plot(threads, eff_2048, marker='s', label="N=2048")
plt.plot(threads, eff_4096, marker='^', label="N=4096")

for t,e in zip(threads, eff_1024):
    plt.text(t, e, f"{e:.2f}", fontsize=7, ha='center')
for t,e in zip(threads, eff_2048):
    plt.text(t, e, f"{e:.2f}", fontsize=7, ha='center')
for t,e in zip(threads, eff_4096):
    plt.text(t, e, f"{e:.2f}", fontsize=7, ha='center')

plt.title("Parallel Efficiency vs Threads")
plt.xlabel("Threads")
plt.ylabel("Efficiency (Sp/p)")
plt.xticks(threads)
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()
