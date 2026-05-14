#include <stdio.h>
#include <stdlib.h>
#include <time.h>

typedef struct {
    long long *periods;
    double min_value;
    long long *min_offsets;
    double max_value;
    long long *max_offsets;
    int is_max_harmonic;
} ExtremeResult;

ExtremeResult *run_evaluation_and_track_extremes(int num_chains_extreme,
                                                 long long random_seed,
                                                 long long perioddown,
                                                 long long periodup,
                                                 size_t *count);

char *output_zero_let_min_max_extremes(const char *timestamp,
                                       const ExtremeResult *results,
                                       size_t count,
                                       int num_chains_extreme,
                                       long long perioddown,
                                       long long periodup);

void free_extreme_results(ExtremeResult *results, size_t count);

static void timestamp_from_seed(long long seed, char *buf, size_t len)
{
    time_t t = (time_t)seed;
    struct tm *tm_info = localtime(&t);

    if (!tm_info) {
        snprintf(buf, len, "unknown_time");
        return;
    }
    strftime(buf, len, "%Y%m%d_%H%M%S", tm_info);
}

int main(int argc, char **argv)
{
    long long perioddown = 2;
    long long periodup = 12;
    int num_chains_extreme = 3;
    long long random_seed = (long long)time(NULL);
    char timestamp[64];
    size_t count = 0;
    ExtremeResult *results;
    char *csvfile;

    if (argc >= 4) {
        perioddown = atoll(argv[1]);
        periodup = atoll(argv[2]);
        num_chains_extreme = atoi(argv[3]);
    }
    if (argc >= 5) {
        random_seed = atoll(argv[4]);
    }

    if (perioddown > periodup || num_chains_extreme <= 0) {
        fprintf(stderr, "Usage: %s [perioddown periodup num_chains_extreme [random_seed]]\n", argv[0]);
        return 1;
    }

    timestamp_from_seed(random_seed, timestamp, sizeof(timestamp));

    results = run_evaluation_and_track_extremes(num_chains_extreme,
                                                random_seed,
                                                perioddown,
                                                periodup,
                                                &count);
    if (!results) {
        fprintf(stderr, "extremes evaluation failed\n");
        return 1;
    }

    csvfile = output_zero_let_min_max_extremes(timestamp,
                                              results,
                                              count,
                                              num_chains_extreme,
                                              perioddown,
                                              periodup);
    if (csvfile) {
        printf("Extreme results saved to %s\n", csvfile);
        free(csvfile);
    }

    free_extreme_results(results, count);
    return 0;
}
