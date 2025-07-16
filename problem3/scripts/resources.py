import re
import matplotlib.pyplot as plt

input_file = "slurm_output_107963.txt"

pattern_threads = re.compile(r"threads=(\d+)")
pattern_real = re.compile(r"real\s+(\dm[\d\.]+s)")
pattern_user = re.compile(r"user\s+(\dm[\d\.]+s)")
pattern_sys = re.compile(r"sys\s+(\dm[\d\.]+s)")

data = []

with open(input_file, "r") as f:
    threads = None
    real = user = sys = None

    for line in f:
        m_threads = pattern_threads.search(line)
        if m_threads:
            threads = int(m_threads.group(1))

        m_real = pattern_real.search(line)
        if m_real:
            real = m_real.group(1)

        m_user = pattern_user.search(line)
        if m_user:
            user = m_user.group(1)

        m_sys = pattern_sys.search(line)
        if m_sys:
            sys = m_sys.group(1)

            # Quando hai tutti e tre, salva
            def time_to_sec(tstr):
                m = re.match(r"(\d+)m([\d\.]+)s", tstr)
                return int(m.group(1)) * 60 + float(m.group(2))

            real_s = time_to_sec(real)
            user_s = time_to_sec(user)
            sys_s = time_to_sec(sys)
            usage = (user_s + sys_s) / real_s

            data.append((threads, usage))

# Raggruppa
data_sorted = sorted(data)
threads_list = [x[0] for x in data_sorted]
usage_list = [x[1] for x in data_sorted]

plt.figure(figsize=(10,6))
plt.plot(threads_list, usage_list, marker='o')
for t, u in zip(threads_list, usage_list):
    plt.text(t, u, f"{u:.1f}×", ha='center', va='bottom', fontsize=8)

plt.xlabel("Number of Threads")
plt.ylabel("CPU Usage (user+sys)/real")
plt.title("CPU Usage Factor vs Threads")
plt.xticks(threads_list)
plt.grid(True)
plt.tight_layout()
plt.show()
