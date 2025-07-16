#!/bin/bash
#SBATCH --job-name=cpu_check
#SBATCH --output=cpu_check.txt
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:01:00
#SBATCH --partition=cpu_sapphire

# Stampiamo informazioni di base
echo "===== lscpu ====="
lscpu

echo "SLURM_CPUS_ON_NODE: $SLURM_CPUS_ON_NODE"
echo "SLURM_JOB_CPUS_PER_NODE: $SLURM_JOB_CPUS_PER_NODE"
echo "SLURM_TASKS_PER_NODE: $SLURM_TASKS_PER_NODE"
