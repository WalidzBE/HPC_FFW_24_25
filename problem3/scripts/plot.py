import numpy as np
import matplotlib.pyplot as plt
import os

def plot_heatmap(iteration):
    filename = f"heatmap_iter_{iteration}.bin"
    with open(filename, 'rb') as f:
        N = np.fromfile(f, dtype=np.int32, count=2)  # Leggi dimensioni N, N
        matrix = np.fromfile(f, dtype=np.float64).reshape(N[0], N[1])
    
    plt.imshow(matrix, cmap='hot', interpolation='nearest')
    plt.colorbar()
    plt.title(f"Heat Diffusion (Iteration {iteration})")
    plt.savefig(f"heatmap_iter_{iteration}.png")
    plt.close()

# Esempio: plot per tutte le iterazioni salvate
for filename in os.listdir('.'):
    if filename.startswith("heatmap_iter_") and filename.endswith(".bin"):
        iter = int(filename.split('_')[2].split('.')[0])
        plot_heatmap(iter)