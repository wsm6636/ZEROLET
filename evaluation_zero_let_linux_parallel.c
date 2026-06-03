#define ZEROLET_EVALUATION_NO_MAIN
#include "evaluation_zero_let.c"

#include <pthread.h>

typedef struct {
    unsigned long long state;
} LocalRng;

typedef struct {
    ExperimentResult *result;
    int repeat;
    int num_repeats;
    long long total_offsets;
    long long processed_offsets;
    long long next_report;
    long long report_step;
} ProgressContext;

typedef struct {
    int n;
    int repeat;
    int num_repeats;
    const long long *period_choices;
    int n_choices;
    long long seed;
    ExperimentResult *result;
    int status;
} ExperimentJob;

static long long g_c_limit = ZEROLET_C_LIMIT;
static long long g_offset_space_limit = ZEROLET_OFFSET_SPACE_LIMIT;

static unsigned int local_rand(LocalRng *rng)
{
    rng->state = rng->state * 6364136223846793005ULL + 1442695040888963407ULL;
    return (unsigned int)(rng->state >> 32);
}

static long long local_choice(LocalRng *rng, const long long *choices, int n_choices)
{
    unsigned int value = local_rand(rng);
    return choices[value % (unsigned int)n_choices];
}

static int choose_periods_with_limit(int n,
                                     const long long *period_choices,
                                     int n_choices,
                                     long long seed,
                                     long long *periods,
                                     long long **G_out,
                                     long long *C_out,
                                     long long *space_size_out)
{
    LocalRng rng;
    int trial = 0;

    rng.state = (unsigned long long)seed ^ ((unsigned long long)n << 32);

    while (1) {
        long long *G;

        for (int i = 0; i < n; i++) {
            periods[i] = local_choice(&rng, period_choices, n_choices);
        }

        G = generate_offsets_eq27_g(periods, n);
        if (!G) {
            return -1;
        }

        *C_out = compute_complexity_eq28(periods, n);
        *space_size_out = offset_space_size_from_g(G, n);

        if (*C_out <= g_c_limit && *space_size_out <= g_offset_space_limit) {
            *G_out = G;
            if (trial > 0) {
                printf("[n=%d] accepted periods after %d retries: C=%lld, offset_space=%lld\n",
                       n,
                       trial,
                       *C_out,
                       *space_size_out);
                fflush(stdout);
            }
            return 0;
        }

        free(G);
        trial++;
        if (trial % 100 == 0) {
            printf("[n=%d] retry %d, last rejected: C=%lld, offset_space=%lld, limits=(%lld,%lld)\n",
                   n,
                   trial,
                   *C_out,
                   *space_size_out,
                   g_c_limit,
                   g_offset_space_limit);
            fflush(stdout);
        }

        if (trial > 1000) {
            static const long long fallback_choices[] = {1, 2, 5, 10, 20, 50};
            for (int i = 0; i < n; i++) {
                periods[i] = local_choice(&rng, fallback_choices, 6);
            }

            G = generate_offsets_eq27_g(periods, n);
            if (!G) {
                return -1;
            }

            *C_out = compute_complexity_eq28(periods, n);
            *space_size_out = offset_space_size_from_g(G, n);
            if (*C_out <= g_c_limit && *space_size_out <= g_offset_space_limit) {
                *G_out = G;
                printf("[n=%d] accepted fallback periods after %d retries: C=%lld, offset_space=%lld\n",
                       n,
                       trial,
                       *C_out,
                       *space_size_out);
                fflush(stdout);
                return 0;
            }
            free(G);
        }
    }
}

static void evaluate_offset_with_progress(const long long *offsets, int n, void *ctx)
{
    ProgressContext *progress = (ProgressContext *)ctx;
    ExperimentResult *result = progress->result;
    AnalysisResult analysis;

    if (run_analysis_zero_let(n, result->periods, offsets, offsets, 0.0, &analysis) != 0) {
        return;
    }

    if (analysis.stats.max < result->min_latency) {
        result->min_latency = analysis.stats.max;
        memcpy(result->min_offsets, offsets, (size_t)n * sizeof(long long));
    }

    if (analysis.stats.max > result->max_latency) {
        result->max_latency = analysis.stats.max;
        memcpy(result->max_offsets, offsets, (size_t)n * sizeof(long long));
    }

    free_analysis_result(&analysis);

    progress->processed_offsets++;
    if (progress->total_offsets > 0 &&
        progress->processed_offsets >= progress->next_report) {
        double pct = 100.0 * (double)progress->processed_offsets / (double)progress->total_offsets;
        if (pct > 100.0) {
            pct = 100.0;
        }
        printf("[n=%d repeat=%d/%d] progress %.1f%% (%lld/%lld)\n",
               result->n,
               progress->repeat + 1,
               progress->num_repeats,
               pct,
               progress->processed_offsets,
               progress->total_offsets);
        fflush(stdout);
        progress->next_report += progress->report_step;
    }
}

static int run_single_experiment_parallel(const ExperimentJob *job)
{
    long long *G = NULL;
    long long space_size = 0;
    double start;
    double end;
    ProgressContext progress;
    ExperimentResult *result = job->result;

    memset(result, 0, sizeof(*result));
    result->n = job->n;
    result->seed = job->repeat + 1;
    result->periods = (long long *)calloc((size_t)job->n, sizeof(long long));
    result->min_offsets = (long long *)calloc((size_t)job->n, sizeof(long long));
    result->max_offsets = (long long *)calloc((size_t)job->n, sizeof(long long));
    if (!result->periods || !result->min_offsets || !result->max_offsets) {
        return -1;
    }

    if (choose_periods_with_limit(job->n,
                                  job->period_choices,
                                  job->n_choices,
                                  job->seed + (long long)job->repeat * 1000003LL + (long long)job->n * 9176LL,
                                  result->periods,
                                  &G,
                                  &result->C,
                                  &space_size) != 0 || !G) {
        return -1;
    }

    printf("[n=%d repeat=%d/%d] started\n", job->n, job->repeat + 1, job->num_repeats);
    print_offset_ranges(result->periods, job->n);

    result->min_latency = DBL_MAX;
    result->max_latency = -DBL_MAX;

    progress.result = result;
    progress.repeat = job->repeat;
    progress.num_repeats = job->num_repeats;
    progress.total_offsets = space_size;
    progress.processed_offsets = 0;
    progress.report_step = space_size / 10;
    if (progress.report_step <= 0) {
        progress.report_step = 1;
    }
    progress.next_report = progress.report_step;

    start = now_seconds();
    generate_offsets_eq27(G, job->n, evaluate_offset_with_progress, &progress);
    end = now_seconds();

    result->R = end - start;
    result->R_over_C = result->C > 0 ? result->R / (double)result->C : 0.0;

    printf("[n=%d repeat=%d/%d] completed: C=%lld, offsets=%lld, R=%.6f seconds, R/C=%.6e, Min=%.3f, Max=%.3f\n",
           job->n,
           job->repeat + 1,
           job->num_repeats,
           result->C,
           space_size,
           result->R,
           result->R_over_C,
           result->min_latency,
           result->max_latency);
    fflush(stdout);

    free(G);
    return 0;
}

static void *experiment_thread_main(void *arg)
{
    ExperimentJob *job = (ExperimentJob *)arg;
    job->status = run_single_experiment_parallel(job);
    return NULL;
}

int main(int argc, char **argv)
{
    int num_limit = 3;
    int num_chains = 6;
    int num_repeats = 1;
    long long period_choices[] = {1, 2, 5, 10, 20, 50, 100, 200, 500, 1000};
    int n_choices = (int)(sizeof(period_choices) / sizeof(period_choices[0]));
    long long random_seed = (long long)time(NULL);
    char timestamp[64];
    size_t job_count;
    ExperimentResult *results;
    ExperimentJob *jobs;
    pthread_t *threads;
    size_t used = 0;
    char *csvfile;

    if (argc >= 2) {
        num_limit = atoi(argv[1]);
    }
    if (argc >= 3) {
        num_chains = atoi(argv[2]);
    }
    if (argc >= 4) {
        num_repeats = atoi(argv[3]);
    }
    if (argc >= 5) {
        random_seed = atoll(argv[4]);
    }
    if (argc >= 6) {
        g_c_limit = atoll(argv[5]);
    }
    if (argc >= 7) {
        g_offset_space_limit = atoll(argv[6]);
    }

    if (argc > 7 ||
        num_limit <= 0 ||
        num_chains < num_limit ||
        num_repeats <= 0 ||
        g_c_limit <= 0 ||
        g_offset_space_limit <= 0) {
        fprintf(stderr, "Usage: %s [num_limit num_chains num_repeats [random_seed [c_limit offset_space_limit]]]\n", argv[0]);
        fprintf(stderr, "Example: %s 3 6 1 12345 10000000000 1000000\n", argv[0]);
        return 1;
    }

    printf("Limits: C <= %lld, offset_space <= %lld\n", g_c_limit, g_offset_space_limit);

    job_count = (size_t)(num_chains - num_limit + 1) * (size_t)num_repeats;
    results = (ExperimentResult *)calloc(job_count, sizeof(ExperimentResult));
    jobs = (ExperimentJob *)calloc(job_count, sizeof(ExperimentJob));
    threads = (pthread_t *)calloc(job_count, sizeof(pthread_t));
    if (!results || !jobs || !threads) {
        fprintf(stderr, "allocation failed\n");
        free(results);
        free(jobs);
        free(threads);
        return 1;
    }

    timestamp_from_seed(random_seed, timestamp, sizeof(timestamp));

    for (int repeat = 0; repeat < num_repeats; repeat++) {
        for (int n = num_limit; n <= num_chains; n++) {
            size_t idx = used++;
            jobs[idx].n = n;
            jobs[idx].repeat = repeat;
            jobs[idx].num_repeats = num_repeats;
            jobs[idx].period_choices = period_choices;
            jobs[idx].n_choices = n_choices;
            jobs[idx].seed = random_seed;
            jobs[idx].result = &results[idx];
            jobs[idx].status = -1;

            if (pthread_create(&threads[idx], NULL, experiment_thread_main, &jobs[idx]) != 0) {
                fprintf(stderr, "failed to create thread for n=%d repeat=%d\n", n, repeat + 1);
                jobs[idx].status = -1;
            }
        }
    }

    for (size_t i = 0; i < used; i++) {
        pthread_join(threads[i], NULL);
    }

    csvfile = output_zero_let(timestamp, num_chains, num_repeats, random_seed, results, used);
    if (csvfile) {
        char *plotfile = write_runtime_svg(results, used, num_chains, num_repeats, random_seed, timestamp);
        char *normalized_plotfile = write_normalized_runtime_svg(results, used, num_chains, num_repeats, random_seed, timestamp);

        printf("Results saved to %s\n", csvfile);
        if (plotfile) {
            printf("Runtime plot saved to %s\n", plotfile);
            free(plotfile);
        }
        if (normalized_plotfile) {
            printf("Normalized runtime plot saved to %s\n", normalized_plotfile);
            free(normalized_plotfile);
        }
        free(csvfile);
    }

    for (size_t i = 0; i < used; i++) {
        free_experiment_result(&results[i]);
    }
    free(results);
    free(jobs);
    free(threads);
    return 0;
}
