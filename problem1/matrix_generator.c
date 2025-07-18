#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/stat.h>

static int adjust_size(int base, int threads)
{
    int rem = base % threads;
    if (rem == 0) return base;
    int down = base - rem;
    int up   = base + (threads - rem);
    /* choose the closer of the two, prefer rounding *up* on a tie */
    return (base - down <= up - base) ? (down > 0 ? down : up) : up;
}

static int file_exists(const char *path)
{
    struct stat sb; return (stat(path, &sb) == 0);
}

static double rnd_double(void)
{
    return rand() / (double)RAND_MAX;
}

static void write_matrix_csv(const char *path, int N)
{
    if (file_exists(path)) return;   /* already there, skip */
    FILE *fp = fopen(path, "w");
    if (!fp) { perror(path); exit(EXIT_FAILURE); }
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            fprintf(fp, "%.10g%c", rnd_double(), (j == N - 1) ? '\n' : ',');
        }
    }
    fclose(fp);
}

int main(int argc, char **argv)
{
    if (argc != 4) {
        fprintf(stderr, "Usage: %s <base_N> <threads> <output_dir>\n", argv[0]);
        return EXIT_FAILURE;
    }

    int base_N   = atoi(argv[1]);
    int threads  = atoi(argv[2]);
    const char *outdir = argv[3];

    if (base_N <= 0 || threads <= 0) {
        fprintf(stderr, "Sizes and thread count must be positive.\n");
        return EXIT_FAILURE;
    }

    /* compute compatible size */
    int N = adjust_size(base_N, threads);

    /* seed RNG distinctly */
    srand((unsigned)(time(NULL) ^ (N * 2654435761u) ^ (threads << 16)));

    /* build file paths */
    char pathA[1024], pathB[1024];
    snprintf(pathA, sizeof pathA, "%s/A%d.csv", outdir, N);
    snprintf(pathB, sizeof pathB, "%s/B%d.csv", outdir, N);

    write_matrix_csv(pathA, N);
    write_matrix_csv(pathB, N);

    /* echo final size for scripts */
    printf("%d\n", N);
    return 0;
}

