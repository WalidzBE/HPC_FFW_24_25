#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <sys/resource.h>   


static double *xmalloc(size_t nbytes)
{
    double *p = (double *)malloc(nbytes);
    if (!p) {
        fprintf(stderr, "Out of memory (%.0f MB)\n", (double)nbytes / (1024 * 1024));
        MPI_Abort(MPI_COMM_WORLD, 2);
    }
    return p;
}

static int detect_matrix_size(const char *fname)
{
    FILE *fp = fopen(fname, "r");
    if (!fp) { perror(fname); MPI_Abort(MPI_COMM_WORLD, 1); }
    int ch, rows = 0, cols = 1, first = 1, last = '\0';
    while ((ch = fgetc(fp)) != EOF) {
        if (ch == ',') { if (first) ++cols; }
        else if (ch == '\n') { ++rows; first = 0; }
        last = ch;
    }
    if (last != '\n') ++rows;
    fclose(fp);
    if (rows != cols) {
        fprintf(stderr, "%s: not square (%d×%d)\n", fname, rows, cols);
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
    return rows;
}

static void read_full_matrix(const char *fname, double *M, int n)
{
    FILE *fp = fopen(fname, "r");
    if (!fp) { perror(fname); MPI_Abort(MPI_COMM_WORLD, 1); }
    for (int i = 0; i < n * n; ++i)
        if (fscanf(fp, "%lf%*[,\n]", &M[i]) != 1) {
            fprintf(stderr, "Parse error in %s\n", fname); MPI_Abort(MPI_COMM_WORLD, 1);
        }
    fclose(fp);
}

static void write_full_matrix(const char *fname, const double *M, int n)
{
    FILE *fp = fopen(fname, "w");
    if (!fp) { perror(fname); MPI_Abort(MPI_COMM_WORLD, 1); }
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j)
            fprintf(fp, "%.10g%c", M[i * n + j], j == n - 1 ? '\n' : ',');
    }
    fclose(fp);
}

static void dgemm_tile(const double *A, const double *B, double *C, int bs)
{
    for (int i = 0; i < bs; ++i)
        for (int k = 0; k < bs; ++k)
            for (int j = 0; j < bs; ++j)
                C[i * bs + j] += A[i * bs + k] * B[k * bs + j];
}

int main(int argc, char **argv)
{

    MPI_Init(&argc, &argv);
    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (argc < 4 || argc > 5) {
        if (rank == 0)
            fprintf(stderr, "Usage: %s A.csv B.csv C.csv [stats.txt]\n", argv[0]);
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    const char *Afile     = argv[1];
    const char *Bfile     = argv[2];
    const char *Cfile     = argv[3];
    const char *statsfile = (argc == 5) ? argv[4] : NULL;   
    int N;
    if (rank == 0) N = detect_matrix_size(Afile);
    MPI_Bcast(&N, 1, MPI_INT, 0, MPI_COMM_WORLD);

    int p = (int)round(sqrt((double)size));
    if (p * p != size || N % p) {
        if (rank == 0)
            fprintf(stderr, "P must be a perfect square and N divisible by √P.\n");
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
    const int bs = N / p;
    const int my_row = rank / p, my_col = rank % p;

    double *Ablk = xmalloc((size_t)bs * bs * sizeof *Ablk);
    double *Bblk = xmalloc((size_t)bs * bs * sizeof *Bblk);
    double *Cblk = calloc((size_t)bs * bs, sizeof *Cblk);
    double *A_in = xmalloc((size_t)bs * bs * sizeof *A_in);
    double *B_in = xmalloc((size_t)bs * bs * sizeof *B_in);


    double *A_rowbuf = (my_col == 0) ? xmalloc((size_t)p * bs * bs * sizeof(double)) : NULL;
    double *B_colbuf = (my_row == 0) ? xmalloc((size_t)p * bs * bs * sizeof(double)) : NULL;


    if (rank == 0) {
        double *A = xmalloc((size_t)N * N * sizeof *A);
        double *B = xmalloc((size_t)N * N * sizeof *B);
        read_full_matrix(Afile, A, N);
        read_full_matrix(Bfile, B, N);


        for (int r = 0; r < p; ++r) {
            double *rowbuf = xmalloc((size_t)p * bs * bs * sizeof *rowbuf);
            for (int k = 0; k < p; ++k)
                for (int i = 0; i < bs; ++i)
                    memcpy(&rowbuf[k * bs * bs + i * bs],
                           &A[(r * bs + i) * N + k * bs], bs * sizeof(double));
            int dest = r * p;   /* column 0 */
            if (dest == 0) memcpy(A_rowbuf, rowbuf, (size_t)p * bs * bs * sizeof(double));
            else MPI_Send(rowbuf, p * bs * bs, MPI_DOUBLE, dest, 10 + r, MPI_COMM_WORLD);
            free(rowbuf);
        }

        for (int c = 0; c < p; ++c) {
            double *colbuf = xmalloc((size_t)p * bs * bs * sizeof *colbuf);
            for (int k = 0; k < p; ++k)
                for (int i = 0; i < bs; ++i)
                    memcpy(&colbuf[k * bs * bs + i * bs],
                           &B[(k * bs + i) * N + c * bs], bs * sizeof(double));
            int dest = c;   /* row 0 */
            if (dest == 0) memcpy(B_colbuf, colbuf, (size_t)p * bs * bs * sizeof(double));
            else MPI_Send(colbuf, p * bs * bs, MPI_DOUBLE, dest, 20 + c, MPI_COMM_WORLD);
            free(colbuf);
        }
        free(A); free(B);
    } else {
        if (my_col == 0)
            MPI_Recv(A_rowbuf, p * bs * bs, MPI_DOUBLE, 0, 10 + my_row, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        if (my_row == 0)
            MPI_Recv(B_colbuf, p * bs * bs, MPI_DOUBLE, 0, 20 + my_col, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
    }

    memset(Ablk, 0, (size_t)bs * bs * sizeof(double));
    memset(Bblk, 0, (size_t)bs * bs * sizeof(double));

    if (my_row == 0 && my_col == 0) {
        memcpy(Ablk, &A_rowbuf[0], (size_t)bs * bs * sizeof(double));
        memcpy(Bblk, &B_colbuf[0], (size_t)bs * bs * sizeof(double));
    }

   
    MPI_Barrier(MPI_COMM_WORLD);
    double t0 = MPI_Wtime();

    const int stages = 3 * p - 2;  /* full pipeline length */
    for (int s = 0; s < stages; ++s) {
        MPI_Request req[4];
        int nreq = 0;
        int east  = (my_col < p - 1) ? rank + 1 : MPI_PROC_NULL;
        int south = (my_row < p - 1) ? rank + p : MPI_PROC_NULL;
        int west  = (my_col > 0)     ? rank - 1 : MPI_PROC_NULL;
        int north = (my_row > 0)     ? rank - p : MPI_PROC_NULL;

        if (east  != MPI_PROC_NULL)
            MPI_Isend(Ablk, bs * bs, MPI_DOUBLE, east, 100, MPI_COMM_WORLD, &req[nreq++]);
        if (south != MPI_PROC_NULL)
            MPI_Isend(Bblk, bs * bs, MPI_DOUBLE, south, 101, MPI_COMM_WORLD, &req[nreq++]);

        int have_A = 0, have_B = 0;
        if (west != MPI_PROC_NULL) {
            MPI_Irecv(A_in, bs * bs, MPI_DOUBLE, west, 100, MPI_COMM_WORLD, &req[nreq++]);
            have_A = -1;
        } else if (my_col == 0) {
            int idx = s - my_row;  /* initial skew */
            if (idx >= 0 && idx < p) {
                memcpy(A_in, &A_rowbuf[idx * bs * bs], (size_t)bs * bs * sizeof(double));
                have_A = 1;
            }
        }

        if (north != MPI_PROC_NULL) {
            MPI_Irecv(B_in, bs * bs, MPI_DOUBLE, north, 101, MPI_COMM_WORLD, &req[nreq++]);
            have_B = -1;
        } else if (my_row == 0) {
            int idx = s - my_col;
            if (idx >= 0 && idx < p) {
                memcpy(B_in, &B_colbuf[idx * bs * bs], (size_t)bs * bs * sizeof(double));
                have_B = 1;
            }
        }

        if (nreq) MPI_Waitall(nreq, req, MPI_STATUSES_IGNORE);
        if (have_A == -1) have_A = 1;
        if (have_B == -1) have_B = 1;

        if (have_A) memcpy(Ablk, A_in, (size_t)bs * bs * sizeof(double));
        if (have_B) memcpy(Bblk, B_in, (size_t)bs * bs * sizeof(double));

        int k = s - my_row - my_col;
        if (k >= 0 && k < p) dgemm_tile(Ablk, Bblk, Cblk, bs);
    }

    double t1 = MPI_Wtime();
    double local_t = t1 - t0, max_t;
    MPI_Reduce(&local_t, &max_t, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);

    if (rank == 0) {
        double *C = xmalloc((size_t)N * N * sizeof *C);
        for (int i = 0; i < bs; ++i)
            memcpy(&C[i * N], &Cblk[i * bs], bs * sizeof(double));

        for (int r = 1; r < size; ++r) {
            double *tmp = xmalloc((size_t)bs * bs * sizeof *tmp);
            MPI_Recv(tmp, bs * bs, MPI_DOUBLE, r, 200, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            int i = r / p, j = r % p;
            for (int ii = 0; ii < bs; ++ii)
                memcpy(&C[(i * bs + ii) * N + j * bs], &tmp[ii * bs], bs * sizeof(double));
            free(tmp);
        }
        write_full_matrix(Cfile, C, N);
        free(C);
    } else {
        MPI_Send(Cblk, bs * bs, MPI_DOUBLE, 0, 200, MPI_COMM_WORLD);
    }


    struct rusage ru;
    getrusage(RUSAGE_SELF, &ru);
    long memKB = ru.ru_maxrss;   /* resident set size of this rank */
    long max_memKB;
    MPI_Reduce(&memKB, &max_memKB, 1, MPI_LONG, MPI_MAX, 0, MPI_COMM_WORLD);

    double cpu_time = ru.ru_utime.tv_sec + ru.ru_utime.tv_usec / 1e6 +
                      ru.ru_stime.tv_sec + ru.ru_stime.tv_usec / 1e6;

    if (rank == 0 && statsfile) {
        FILE *fp = fopen(statsfile, "a");
        if (fp) {
            fprintf(fp, "N=%d P=%d time=%f cpu=%f memKB=%ld\n",
                    N, size, max_t, cpu_time, max_memKB);
            fclose(fp);
        } else {
            fprintf(stderr, "Cannot open %s for writing\n", statsfile);
        }
        printf("Finished C=A×B  N=%d  P=%d  %fs (peak mem %.1f MB)\n",
               N, size, max_t, max_memKB / 1024.0);
    }
    MPI_Finalize();

    free(Ablk); free(Bblk); free(Cblk);
    free(A_in); free(B_in);
    if (A_rowbuf) free(A_rowbuf);
    if (B_colbuf) free(B_colbuf);

    
    return 0;
}




