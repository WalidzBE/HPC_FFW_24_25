#!/bin/bash
#SBATCH --job-name=matmul-2strat
#SBATCH --partition=cpu_sapphire          # Sapphire Rapids CPU nodes
#SBATCH --nodes=2                         # allocate two nodes (needed by strategy 2)
#SBATCH --ntasks=90                       # enough ranks for 49 per node
#SBATCH --ntasks-per-node=49              # cap ranks per node
#SBATCH --cpus-per-task=1
#SBATCH --time=00:30:00
#SBATCH --mem=1G
#SBATCH --output=mmul_2strat_%j.out
#SBATCH --error=mmul_2strat_%j.err

module purge
module load openmpi/4.1.8_gcc11          

# Slurm integration: avoid ssh fallback
export OMPI_MCA_pml=ob1
export OMPI_MCA_btl=self,tcp



GEN=$HOME/filippo/bin/matrix_generator      # random matrix generator
MMUL=$HOME/filippo/bin/matrix_mul           # instrumented matrix multiply
DATADIR=$HOME/filippo/data/matrices         # where A_N.csv / B_N.csv live
OUTDIR=$SLURM_SUBMIT_DIR/results_$SLURM_JOB_ID
mkdir -p "$DATADIR" "$OUTDIR"
cd       "$OUTDIR"

STAT1=$OUTDIR/stats_strategy1.txt           # aggregate file for strategy 1
STAT2=$OUTDIR/stats_strategy2.txt           # aggregate file for strategy 2
: >"$STAT1" : >"$STAT2"

bases=(100 200 500)
ranks=(1 4 9 16 25 36 49 64)                      # perfect‑square ranks
rep=10


run_case () {
    local base=$1 nt=$2 nodes=$3 sid=$4

    local statsfile; [[ $sid -eq 1 ]] && statsfile=$STAT1 || statsfile=$STAT2

    local N=$("$GEN" "$base" "$nt" "$DATADIR")
    local A="$DATADIR/A${N}.csv"
    local B="$DATADIR/B${N}.csv"
    local C="C${N}_s${sid}.csv"

    # Launch ranks with Slurm's PMI interface
    srun --mpi=pmix -N "$nodes" -n "$nt" "$MMUL" "$A" "$B" "$C" "$statsfile"
}


for base in "${bases[@]}"; do
  for nt in "${ranks[@]}"; do

    ######## Strategy 1 – fill node 0 then spill ########
    if (( nt <= 49 )); then
        nodes1=1
    else
        nodes1=2
    fi
    for ((r=1; r<=rep; ++r)); do
        run_case "$base" "$nt" "$nodes1" 1
    done

    ######## Strategy 2 – always two nodes, balanced ########
    nodes2=2
    for ((r=1; r<=rep; ++r)); do
        run_case "$base" "$nt" "$nodes2" 2
    done

  done
done
