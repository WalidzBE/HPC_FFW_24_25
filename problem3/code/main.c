#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <omp.h>

//costanti di temperatura 
#define T_AVG 15.0 
#define T_HOT_A 250.0
#define T_HOT_B 540.0

//pesi per diffusione anisotropica 
#define W_x 0.3
#define W_y 0.2


//******************************************* */
//Convertire coordinate 2D in indice 1D

static int index(int i, int j, int N){

    return i*N + j;
}

//************************************** */
//Inizializzazione della griglia

void init_plate (double *grid, int N, int mode){


    for(int i=0; i<N; i++){

        for(int j=0; j< N; j++)
        {

            if(mode==0){

                
                if(j<N/2) //sinistra della griglia
                    grid[index(i,j, N)]=T_HOT_A;

                else //destra della griglia 
                    grid[index(i, j, N)]= T_AVG;
            }else{ 

                int quarter = N/4;
                int three_quarter = 3*N/4;

                if(i>= quarter && i< three_quarter && j>= quarter && j <three_quarter)
                    grid[index(i, j, N)] = T_HOT_B;
                else
                    grid[index(i, j, N)] = T_AVG;


            }            

        }

    }

}



// Salva la matrice in un file binario (formato: N, N, grid[])
void save_matrix_binary(double *grid, int N, int iteration) {
    char filename[256];
    sprintf(filename, "heatmap_iter_%d.bin", iteration);
    FILE *file = fopen(filename, "wb");
    if (file == NULL) {
        perror("Error opening file");
        return;
    }
    // Scrivi dimensioni N e N (opzionale, utile per Python)
    fwrite(&N, sizeof(int), 1, file);
    fwrite(&N, sizeof(int), 1, file);
    // Scrivi la matrice
    fwrite(grid, sizeof(double), N * N, file);
    fclose(file);
}


int main (int argc, char **argv)
{

    int N;
    int mode;
    double eps;
    int max_iter;
    int sample;

    //Leggiamo gli argomenti dalla riga di comando

    if(argc > 1)
        N=atoi(argv[1]);
    else
        N=1024;

    if(argc>2)
        mode= atoi(argv[2]);
    else
        mode = 0;
    
    //soglia di convergenza --> se variazione di temperatura diventa più piccola di eps
    //--> soluzione si è stabilizzata
    if(argc > 3)
        eps = atof(argv[3]);
    else
        eps=1e-3; //trade-off 

    if (argc > 4)
        max_iter = atoi(argv[4]);
    else
        max_iter = 10000;
    
    //Ogni quante operazioni stampiamo deltaT
    if (argc > 5)
        sample = atoi(argv[5]);
    else
        sample = 200;
    
    double *grid = (double *)calloc(N*N, sizeof(double)); //matrice attuale
    double *next = (double *)calloc(N*N, sizeof(double)); //matrice temporanea

    if(grid==NULL || next==NULL){

        printf("\n Not enough memory available!");

    }

    init_plate(grid, N, mode);


    //Ciclo iterazioni

    double start_time = omp_get_wtime();
    int iter;
    double max_difference = 0.0;

    for (iter =1; iter <=max_iter; iter++) //per ogni iterazione
    {

        max_difference = 0.0;

        #pragma omp parallel for collapse(2) reduction(max:max_difference) schedule(static)

        for(int i=0; i < N; i++){

            for (int j=0; j<N; j++){

                
                int center = i*N +j;
                int top = (i-1)*N +j;
                int bottom = (i+1) * N + j;
                int left = i*N + (j-1);
                int right = i*N + (j+1);

                if(j==0){
                    left = i*N + (j);
                }
                if(j==N-1){
                    right = i*N + (j);
                }
                if(i==0){
                    top = (i)*N +j;
                }
                if(i==N-1){
                    bottom = (i) * N + j;
                }

                

                double new_temperature;


                if(mode==0){

                    //media tra i quattro siti adiacenti
                    new_temperature = 0.25 * (grid[top] + grid[bottom] + grid[left] + grid[right]);

                }else{

                    new_temperature = W_x * (grid[left]+ grid[right]) + W_y*(grid[top] + grid[bottom]);


                }
                
                next[center] = new_temperature;

                //valore assoluto float abs
                double diff = fabs(new_temperature - grid[center]);

                //calcoliamo la massima differenza per ogni iterazione
                if(diff > max_difference){ 
                    max_difference= diff;
                }

            }

        }

        //scambio delle matrici
        double *temp = grid;
        grid = next;
        next = temp;

        //solo il thread principale stampa
        if(sample > 0 && iter % sample == 0){

            #pragma omp master
            printf("Iterazione %d ΔT max = %.6f\n", iter, max_difference);
        
        }

        //convergenza?
        if(max_difference <eps){
            break;
        }

    }


            
    double end_time = omp_get_wtime();
    int nt;

    #pragma omp parallel
    {
        #pragma omp master
        nt= omp_get_num_threads(); //quanti thread sono stati usati?
    }

    printf("\nMode %d  N=%d  threads=%d  iters=%d  %.3f ms\n",
       mode, N, nt, iter, (end_time-start_time)*1e3);

    free(grid); free(next);
    return 0;


}