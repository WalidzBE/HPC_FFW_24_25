#!/bin/bash
#SBATCH --job-name=heat_parallel_eval
#SBATCH --output=slurm_output_%j.txt
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=96
#SBATCH --time=02:00:00
#SBATCH --partition=cpu_sapphire

THREAD_LIST="1 2 4 8 16 32 48 64 96"
REPS=5

echo "==================================="
echo "INIZIO ESPERIMENTO"
echo "Thread list: $THREAD_LIST"
echo "Ripetizioni: $REPS"
echo "==================================="

for THREADS in $THREAD_LIST
do
  for (( i=1; i<=REPS; i++ ))
  do
    echo "-----------------------------------"
    echo "RUN $i | Mode 0 | Threads: $THREADS"
    echo "-----------------------------------"
    export OMP_NUM_THREADS=$THREADS

    ./main 1024 0

    echo ""
    echo "== Resource Usage =="
    time ./main 1024 0 > /dev/null
    echo ""

    echo "-----------------------------------"
    echo "RUN $i | Mode 1 | Threads: $THREADS"
    echo "-----------------------------------"
    export OMP_NUM_THREADS=$THREADS

    ./main 1024 1

    echo ""
    echo "== Resource Usage =="
    time ./main 1024 1 > /dev/null
    echo ""

    echo ""
  done
done

echo "==================================="
echo "ESPERIMENTO COMPLETATO!"
echo "==================================="
