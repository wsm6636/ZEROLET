#include "analysis_zero_let.h"

#include <errno.h>
#include <float.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
#include <direct.h>
#define MKDIR(path) _mkdir(path)
#else
#include <sys/stat.h>
#define MKDIR(path) mkdir(path, 0777)
#endif

#define C_RESULTS_DIR "data_c"

typedef struct {
    int n;
    long long *periods;
    long long seed;
    long long C;
    double R;
    double R_over_C;
    double min_latency;
    long long *min_offsets;
    double max_latency;
    long long *max_offsets;
} ExperimentResult;

typedef struct {
    long long *periods;
    double min_value;
    long long *min_offsets;
    double max_value;
    long long *max_offsets;
    int is_max_harmonic;
} ExtremeResult;

typedef void (*period_combo_callback)(const long long *periods, int n, void *ctx);
typedef void (*offset_combo_callback)(const long long *offsets, int n, void *ctx);

static void ensure_data_dir(void)
{
    if (MKDIR(C_RESULTS_DIR) != 0 && errno != EEXIST) {
        fprintf(stderr, "warning: cannot create %s directory\n", C_RESULTS_DIR);
    }
}

static double now_seconds(void)
{
    return (double)clock() / (double)CLOCKS_PER_SEC;
}

static void format_array(char *buf, size_t buf_size, const long long *arr, int n)
{
    size_t used = 0;

    if (buf_size == 0) {
        return;
    }

    used += (size_t)snprintf(buf + used, buf_size - used, "\"[");
    for (int i = 0; i < n && used < buf_size; i++) {
        used += (size_t)snprintf(buf + used,
                                 buf_size - used,
                                 "%lld%s",
                                 arr[i],
                                 (i == n - 1) ? "" : ", ");
    }
    if (used < buf_size) {
        snprintf(buf + used, buf_size - used, "]\"");
    } else {
        buf[buf_size - 1] = '\0';
    }
}

long long count_period_combinations(long long perioddown, long long periodup, int num_chains)
{
    long long range = periodup - perioddown + 1;
    long long total = 1;

    if (range <= 0 || num_chains < 0) {
        return 0;
    }

    for (int i = 0; i < num_chains; i++) {
        total *= range;
    }
    return total;
}

static void generate_period_combinations_rec(long long perioddown,
                                             long long periodup,
                                             int num_chains,
                                             int level,
                                             long long *current,
                                             period_combo_callback cb,
                                             void *ctx)
{
    if (level == num_chains) {
        cb(current, num_chains, ctx);
        return;
    }

    for (long long p = perioddown; p <= periodup; p++) {
        current[level] = p;
        generate_period_combinations_rec(perioddown, periodup, num_chains, level + 1, current, cb, ctx);
    }
}

void generate_period_combinations(long long perioddown,
                                  long long periodup,
                                  int num_chains,
                                  period_combo_callback cb,
                                  void *ctx)
{
    long long *current;

    if (!cb || num_chains < 0 || perioddown > periodup) {
        return;
    }

    current = (long long *)calloc((size_t)num_chains, sizeof(long long));
    if (!current) {
        return;
    }

    generate_period_combinations_rec(perioddown, periodup, num_chains, 0, current, cb, ctx);
    free(current);
}

static void generate_read_combinations_zero_rec(const long long *periods,
                                                int n,
                                                int level,
                                                long long *current,
                                                offset_combo_callback cb,
                                                void *ctx)
{
    long long upper;

    if (level == n) {
        cb(current, n, ctx);
        return;
    }

    if (level == 0) {
        current[level] = 0;
        generate_read_combinations_zero_rec(periods, n, level + 1, current, cb, ctx);
        return;
    }

    upper = periods[level];
    for (long long offset = 0; offset <= upper; offset++) {
        current[level] = offset;
        generate_read_combinations_zero_rec(periods, n, level + 1, current, cb, ctx);
    }
}

void generate_all_read_combinations_zero(const long long *periods,
                                         int n,
                                         offset_combo_callback cb,
                                         void *ctx)
{
    long long *current;

    if (!cb || n < 0) {
        return;
    }

    current = (long long *)calloc((size_t)n, sizeof(long long));
    if (!current) {
        return;
    }

    generate_read_combinations_zero_rec(periods, n, 0, current, cb, ctx);
    free(current);
}

int isMaxHarmonic(const long long *periods, int n)
{
    long long max_period;

    if (!periods || n <= 0) {
        return 0;
    }

    max_period = periods[0];
    for (int i = 1; i < n; i++) {
        if (periods[i] > max_period) {
            max_period = periods[i];
        }
    }

    for (int i = 0; i < n; i++) {
        if (periods[i] == 0 || max_period % periods[i] != 0) {
            return 0;
        }
    }
    return 1;
}

long long *generate_offsets_eq27_g(const long long *periods, int n)
{
    long long *G = (long long *)calloc((size_t)n, sizeof(long long));
    long long H;

    if (!G || !periods || n <= 0) {
        free(G);
        return NULL;
    }

    H = periods[0];
    G[0] = 1;
    for (int i = 1; i < n; i++) {
        G[i] = zerolet_gcd(H, periods[i]);
        H = zerolet_lcm(H, periods[i]);
    }

    return G;
}

long long compute_complexity_eq28(const long long *periods, int n)
{
    long long prod = 1;

    if (!periods || n <= 0) {
        return 0;
    }

    for (int i = 1; i < n; i++) {
        prod *= periods[i];
    }
    return (long long)n * prod;
}

void print_offset_ranges(const long long *periods, int n)
{
    long long *G = generate_offsets_eq27_g(periods, n);
    long long space_size = 1;

    if (!G) {
        return;
    }

    printf("\n=== Offset Design Space (Eq.27) ===\n");
    printf("Periods: [");
    for (int i = 0; i < n; i++) {
        printf("%lld%s", periods[i], (i == n - 1) ? "" : ", ");
    }
    printf("]\n\nOffset ranges:\n");
    printf("phi1 in {0}\n");

    for (int i = 1; i < n; i++) {
        printf("phi%d in [0, %lld]  (G%d=%lld)\n", i + 1, G[i] - 1, i + 1, G[i]);
        space_size *= G[i];
    }

    printf("\nTotal offset space size: %lld\n", space_size);
    free(G);
}

static void generate_eq27_offsets_rec(const long long *G,
                                      int n,
                                      int level,
                                      long long *current,
                                      offset_combo_callback cb,
                                      void *ctx)
{
    if (level == n) {
        cb(current, n, ctx);
        return;
    }

    if (level == 0) {
        current[0] = 0;
        generate_eq27_offsets_rec(G, n, 1, current, cb, ctx);
        return;
    }

    for (long long offset = 0; offset < G[level]; offset++) {
        current[level] = offset;
        generate_eq27_offsets_rec(G, n, level + 1, current, cb, ctx);
    }
}

static void generate_offsets_eq27(const long long *G, int n, offset_combo_callback cb, void *ctx)
{
    long long *current = (long long *)calloc((size_t)n, sizeof(long long));

    if (!current) {
        return;
    }
    generate_eq27_offsets_rec(G, n, 0, current, cb, ctx);
    free(current);
}

static double uniform01(void)
{
    return (double)rand() / ((double)RAND_MAX + 1.0);
}

static long long choice_from(const long long *choices, int n_choices)
{
    int idx = (int)floor(uniform01() * (double)n_choices);
    if (idx >= n_choices) {
        idx = n_choices - 1;
    }
    return choices[idx];
}

static long long offset_space_size_from_g(const long long *G, int n)
{
    long long size = 1;

    for (int i = 1; i < n; i++) {
        size *= G[i];
    }
    return size;
}

static int choose_periods_for_experiment(int n,
                                         const long long *period_choices,
                                         int n_choices,
                                         long long *periods,
                                         long long **G_out,
                                         long long *C_out,
                                         long long *space_size_out)
{
    int trial = 0;

    while (1) {
        long long *G;

        for (int i = 0; i < n; i++) {
            periods[i] = choice_from(period_choices, n_choices);
        }

        G = generate_offsets_eq27_g(periods, n);
        if (!G) {
            return -1;
        }

        *C_out = compute_complexity_eq28(periods, n);
        *space_size_out = offset_space_size_from_g(G, n);

        if (*C_out <= 1000000000LL && *space_size_out <= 100000LL) {
            *G_out = G;
            return 0;
        }

        free(G);
        trial++;
        if (trial > 1000) {
            static const long long fallback_choices[] = {1, 2, 5, 10, 20, 50};
            for (int i = 0; i < n; i++) {
                periods[i] = choice_from(fallback_choices, 6);
            }
        }
    }
}

static void evaluate_eq27_offset(const long long *offsets, int n, void *ctx)
{
    ExperimentResult *result = (ExperimentResult *)ctx;
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
}

int run_single_experiment(int num_chains,
                          const long long *period_choices,
                          int n_choices,
                          long long seed,
                          ExperimentResult *result)
{
    long long *G = NULL;
    long long space_size = 0;
    double start;
    double end;

    if (!period_choices || !result || num_chains <= 0 || n_choices <= 0) {
        return -1;
    }

    memset(result, 0, sizeof(*result));
    result->n = num_chains;
    result->seed = seed;
    result->periods = (long long *)calloc((size_t)num_chains, sizeof(long long));
    result->min_offsets = (long long *)calloc((size_t)num_chains, sizeof(long long));
    result->max_offsets = (long long *)calloc((size_t)num_chains, sizeof(long long));
    if (!result->periods || !result->min_offsets || !result->max_offsets) {
        return -1;
    }

    if (choose_periods_for_experiment(num_chains,
                                      period_choices,
                                      n_choices,
                                      result->periods,
                                      &G,
                                      &result->C,
                                      &space_size) != 0) {
        return -1;
    }

    print_offset_ranges(result->periods, num_chains);

    result->min_latency = DBL_MAX;
    result->max_latency = -DBL_MAX;

    start = now_seconds();
    generate_offsets_eq27(G, num_chains, evaluate_eq27_offset, result);
    end = now_seconds();

    result->R = end - start;
    result->R_over_C = result->C > 0 ? result->R / (double)result->C : 0.0;

    printf("Experiment completed for n=%d: C=%lld, R=%.6f seconds, R/C=%.6e, "
           "Min Latency=%.3f, Max Latency=%.3f\n",
           num_chains,
           result->C,
           result->R,
           result->R_over_C,
           result->min_latency,
           result->max_latency);

    free(G);
    (void)space_size;
    return 0;
}

void free_experiment_result(ExperimentResult *result)
{
    if (!result) {
        return;
    }
    free(result->periods);
    free(result->min_offsets);
    free(result->max_offsets);
    memset(result, 0, sizeof(*result));
}

ExperimentResult *run_evaluation_zero_let(int num_limit,
                                          int num_chains,
                                          int num_repeats,
                                          const long long *period_choices,
                                          int n_choices,
                                          long long random_seed,
                                          size_t *result_count)
{
    size_t cap = (size_t)(num_chains - num_limit + 1) * (size_t)num_repeats;
    ExperimentResult *results = (ExperimentResult *)calloc(cap, sizeof(ExperimentResult));
    size_t used = 0;

    if (!results || !result_count) {
        free(results);
        return NULL;
    }

    for (int repeat = 0; repeat < num_repeats; repeat++) {
        srand((unsigned int)random_seed);
        for (int n = num_limit; n <= num_chains; n++) {
            printf("Running experiment for n=%d, repeat %d/%d...\n", n, repeat + 1, num_repeats);
            if (run_single_experiment(n, period_choices, n_choices, random_seed, &results[used]) == 0) {
                used++;
            }
        }
        random_seed++;
    }

    *result_count = used;
    return results;
}

char *output_zero_let(const char *timestamp,
                      int num_chains,
                      int num_repeats,
                      long long random_seed,
                      const ExperimentResult *results,
                      size_t result_count)
{
    char *path = (char *)calloc(512, sizeof(char));
    FILE *f;

    if (!path) {
        return NULL;
    }

    ensure_data_dir();
    snprintf(path,
             512,
             C_RESULTS_DIR "/data_zero_let_RC_n%d_%d_%lld_%s.csv",
             num_chains,
             num_repeats,
             random_seed,
             timestamp);

    f = fopen(path, "w");
    if (!f) {
        free(path);
        return NULL;
    }

    fprintf(f,
            "n,periods,seed,C,R,R/C,min_latency (LZ-),min_offsets,max_latency (LZ+),max_offsets\n");

    for (size_t i = 0; i < result_count; i++) {
        char periods[1024];
        char min_offsets[1024];
        char max_offsets[1024];

        format_array(periods, sizeof(periods), results[i].periods, results[i].n);
        format_array(min_offsets, sizeof(min_offsets), results[i].min_offsets, results[i].n);
        format_array(max_offsets, sizeof(max_offsets), results[i].max_offsets, results[i].n);

        fprintf(f,
                "%d,%s,%lld,%lld,%.6f,%.6e,%.3f,%s,%.3f,%s\n",
                results[i].n,
                periods,
                results[i].seed,
                results[i].C,
                results[i].R,
                results[i].R_over_C,
                results[i].min_latency,
                min_offsets,
                results[i].max_latency,
                max_offsets);
    }

    fclose(f);
    return path;
}

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

static int style_index_for_n(const int *unique_n, int unique_count, int n)
{
    for (int i = 0; i < unique_count; i++) {
        if (unique_n[i] == n) {
            return i;
        }
    }
    return 0;
}

static void write_svg_marker(FILE *f, double x, double y, int style_idx, const char *color)
{
    int shape = style_idx % 8;

    switch (shape) {
    case 0:
        fprintf(f, "<circle cx=\"%.2f\" cy=\"%.2f\" r=\"5\" fill=\"%s\"/>\n", x, y, color);
        break;
    case 1:
        fprintf(f, "<rect x=\"%.2f\" y=\"%.2f\" width=\"10\" height=\"10\" fill=\"%s\" transform=\"rotate(0 %.2f %.2f)\"/>\n",
                x - 5.0, y - 5.0, color, x, y);
        break;
    case 2:
        fprintf(f, "<polygon points=\"%.2f,%.2f %.2f,%.2f %.2f,%.2f\" fill=\"%s\"/>\n",
                x, y - 6.0, x - 6.0, y + 5.0, x + 6.0, y + 5.0, color);
        break;
    case 3:
        fprintf(f, "<rect x=\"%.2f\" y=\"%.2f\" width=\"10\" height=\"10\" fill=\"%s\" transform=\"rotate(45 %.2f %.2f)\"/>\n",
                x - 5.0, y - 5.0, color, x, y);
        break;
    case 4:
        fprintf(f, "<polygon points=\"%.2f,%.2f %.2f,%.2f %.2f,%.2f\" fill=\"%s\"/>\n",
                x, y + 6.0, x - 6.0, y - 5.0, x + 6.0, y - 5.0, color);
        break;
    case 5:
        fprintf(f, "<line x1=\"%.2f\" y1=\"%.2f\" x2=\"%.2f\" y2=\"%.2f\" stroke=\"%s\" stroke-width=\"3\"/>\n",
                x - 6.0, y, x + 6.0, y, color);
        fprintf(f, "<line x1=\"%.2f\" y1=\"%.2f\" x2=\"%.2f\" y2=\"%.2f\" stroke=\"%s\" stroke-width=\"3\"/>\n",
                x, y - 6.0, x, y + 6.0, color);
        break;
    case 6:
        fprintf(f, "<polygon points=\"%.2f,%.2f %.2f,%.2f %.2f,%.2f %.2f,%.2f\" fill=\"%s\"/>\n",
                x, y - 6.0, x + 6.0, y, x, y + 6.0, x - 6.0, y, color);
        break;
    default:
        fprintf(f, "<circle cx=\"%.2f\" cy=\"%.2f\" r=\"5\" fill=\"none\" stroke=\"%s\" stroke-width=\"2\"/>\n", x, y, color);
        break;
    }
}

static void write_log_tick_label(FILE *f, double x, double y, int exponent, int is_x_axis)
{
    if (exponent == 0) {
        fprintf(f,
                "<text x=\"%.2f\" y=\"%.2f\" text-anchor=\"%s\" font-family=\"Arial\" font-size=\"12\">1</text>\n",
                x,
                y,
                is_x_axis ? "middle" : "end");
        return;
    }

    fprintf(f,
            "<text x=\"%.2f\" y=\"%.2f\" text-anchor=\"%s\" font-family=\"Arial\" font-size=\"12\">10<tspan baseline-shift=\"super\" font-size=\"9\">%d</tspan></text>\n",
            x,
            y,
            is_x_axis ? "middle" : "end",
            exponent);
}

static void write_log_axes(FILE *f,
                           double min_x,
                           double max_x,
                           double min_y,
                           double max_y,
                           double left,
                           double right,
                           double top,
                           double bottom)
{
    int min_x_exp = (int)ceil(log10(min_x));
    int max_x_exp = (int)floor(log10(max_x));
    int min_y_exp = (int)ceil(log10(min_y));
    int max_y_exp = (int)floor(log10(max_y));

    for (int exp = min_x_exp; exp <= max_x_exp; exp++) {
        double value = pow(10.0, (double)exp);
        double x = left + (log10(value) - log10(min_x)) / (log10(max_x) - log10(min_x)) * (right - left);

        fprintf(f, "<line x1=\"%.2f\" y1=\"%.0f\" x2=\"%.2f\" y2=\"%.0f\" stroke=\"#d6d6d6\"/>\n", x, top, x, bottom);
        fprintf(f, "<line x1=\"%.2f\" y1=\"%.0f\" x2=\"%.2f\" y2=\"%.0f\" stroke=\"#222\"/>\n", x, bottom, x, bottom + 6.0);
        write_log_tick_label(f, x, bottom + 22.0, exp, 1);
    }

    for (int exp = min_y_exp; exp <= max_y_exp; exp++) {
        double value = pow(10.0, (double)exp);
        double y = bottom - (log10(value) - log10(min_y)) / (log10(max_y) - log10(min_y)) * (bottom - top);

        fprintf(f, "<line x1=\"%.0f\" y1=\"%.2f\" x2=\"%.0f\" y2=\"%.2f\" stroke=\"#d6d6d6\"/>\n", left, y, right, y);
        fprintf(f, "<line x1=\"%.0f\" y1=\"%.2f\" x2=\"%.0f\" y2=\"%.2f\" stroke=\"#222\"/>\n", left - 6.0, y, left, y);
        write_log_tick_label(f, left - 10.0, y + 4.0, exp, 0);
    }
}

static char *write_runtime_svg(const ExperimentResult *results,
                               size_t result_count,
                               int num_chains,
                               int num_repeats,
                               long long random_seed,
                               const char *timestamp)
{
    char *path = (char *)calloc(512, sizeof(char));
    FILE *f;
    double min_c = DBL_MAX;
    double max_c = -DBL_MAX;
    double min_r = DBL_MAX;
    double max_r = -DBL_MAX;
    const double left = 90.0;
    const double right = 805.0;
    const double top = 70.0;
    const double bottom = 620.0;
    const char *colors[] = {
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"
    };
    int unique_n[64];
    int unique_count = 0;

    if (!path || !results || result_count == 0) {
        free(path);
        return NULL;
    }

    for (size_t i = 0; i < result_count; i++) {
        double c = (double)results[i].C;
        double r = results[i].R;

        if (c <= 0.0) {
            continue;
        }
        if (r <= 0.0) {
            r = 1e-9;
        }

        if (c < min_c) min_c = c;
        if (c > max_c) max_c = c;
        if (r < min_r) min_r = r;
        if (r > max_r) max_r = r;

        if (style_index_for_n(unique_n, unique_count, results[i].n) == 0) {
            int seen = 0;
            for (int j = 0; j < unique_count; j++) {
                if (unique_n[j] == results[i].n) {
                    seen = 1;
                    break;
                }
            }
            if (!seen && unique_count < (int)(sizeof(unique_n) / sizeof(unique_n[0]))) {
                unique_n[unique_count++] = results[i].n;
            }
        }
    }

    if (min_c == DBL_MAX || min_r == DBL_MAX) {
        free(path);
        return NULL;
    }

    if (min_c == max_c) {
        min_c *= 0.8;
        max_c *= 1.2;
    }
    if (min_r == max_r) {
        min_r *= 0.8;
        max_r *= 1.2;
    }

    ensure_data_dir();
    snprintf(path,
             512,
             C_RESULTS_DIR "/zero_let_Runtime_n%d_%d_%lld_%s.svg",
             num_chains,
             num_repeats,
             random_seed,
             timestamp);
    f = fopen(path, "w");
    if (!f) {
        free(path);
        return NULL;
    }

    fprintf(f, "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1000\" height=\"700\" viewBox=\"0 0 1000 700\">\n");
    fprintf(f, "<rect width=\"100%%\" height=\"100%%\" fill=\"white\"/>\n");
    fprintf(f, "<text x=\"500\" y=\"35\" text-anchor=\"middle\" font-family=\"Arial\" font-size=\"22\">Runtime (R) over Complexity (C)</text>\n");
    fprintf(f, "<line x1=\"%.0f\" y1=\"%.0f\" x2=\"%.0f\" y2=\"%.0f\" stroke=\"#222\"/>\n", left, bottom, right, bottom);
    fprintf(f, "<line x1=\"%.0f\" y1=\"%.0f\" x2=\"%.0f\" y2=\"%.0f\" stroke=\"#222\"/>\n", left, top, left, bottom);
    write_log_axes(f, min_c, max_c, min_r, max_r, left, right, top, bottom);

    fprintf(f, "<text x=\"448\" y=\"675\" text-anchor=\"middle\" font-family=\"Arial\" font-size=\"16\">Complexity (C)</text>\n");
    fprintf(f, "<text x=\"24\" y=\"345\" text-anchor=\"middle\" font-family=\"Arial\" font-size=\"16\" transform=\"rotate(-90 24 345)\">Runtime (R) [seconds]</text>\n");

    for (size_t i = 0; i < result_count; i++) {
        double c = (double)results[i].C;
        double r = results[i].R <= 0.0 ? 1e-9 : results[i].R;
        double x = left + (log10(c) - log10(min_c)) / (log10(max_c) - log10(min_c)) * (right - left);
        double y = bottom - (log10(r) - log10(min_r)) / (log10(max_r) - log10(min_r)) * (bottom - top);
        int style_idx = style_index_for_n(unique_n, unique_count, results[i].n);
        const char *color = colors[style_idx % (int)(sizeof(colors) / sizeof(colors[0]))];

        write_svg_marker(f, x, y, style_idx, color);
        fprintf(f, "<title>n=%d, C=%lld, R=%.6f</title>\n", results[i].n, results[i].C, results[i].R);
    }

    fprintf(f, "<text x=\"850\" y=\"95\" font-family=\"Arial\" font-size=\"15\" font-weight=\"bold\">Task chain length</text>\n");
    for (int i = 0; i < unique_count; i++) {
        double y = 125.0 + (double)i * 28.0;
        const char *color = colors[i % (int)(sizeof(colors) / sizeof(colors[0]))];

        write_svg_marker(f, 862.0, y - 5.0, i, color);
        fprintf(f, "<text x=\"882\" y=\"%.2f\" font-family=\"Arial\" font-size=\"14\">n=%d</text>\n", y, unique_n[i]);
    }

    fprintf(f, "</svg>\n");
    fclose(f);
    return path;
}

static char *write_normalized_runtime_svg(const ExperimentResult *results,
                                          size_t result_count,
                                          int num_chains,
                                          int num_repeats,
                                          long long random_seed,
                                          const char *timestamp)
{
    char *path = (char *)calloc(512, sizeof(char));
    FILE *f;
    double min_c = DBL_MAX;
    double max_c = -DBL_MAX;
    double min_y = DBL_MAX;
    double max_y = -DBL_MAX;
    const double left = 90.0;
    const double right = 805.0;
    const double top = 70.0;
    const double bottom = 620.0;
    const char *colors[] = {
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"
    };
    int unique_n[64];
    int unique_count = 0;

    if (!path || !results || result_count == 0) {
        free(path);
        return NULL;
    }

    for (size_t i = 0; i < result_count; i++) {
        double c = (double)results[i].C;
        double y = results[i].R_over_C;
        int seen = 0;

        if (c <= 0.0) {
            continue;
        }
        if (y <= 0.0) {
            y = 1e-12;
        }

        if (c < min_c) min_c = c;
        if (c > max_c) max_c = c;
        if (y < min_y) min_y = y;
        if (y > max_y) max_y = y;

        for (int j = 0; j < unique_count; j++) {
            if (unique_n[j] == results[i].n) {
                seen = 1;
                break;
            }
        }
        if (!seen && unique_count < (int)(sizeof(unique_n) / sizeof(unique_n[0]))) {
            unique_n[unique_count++] = results[i].n;
        }
    }

    if (min_c == DBL_MAX || min_y == DBL_MAX) {
        free(path);
        return NULL;
    }

    if (min_c == max_c) {
        min_c *= 0.8;
        max_c *= 1.2;
    }
    if (min_y == max_y) {
        min_y *= 0.8;
        max_y *= 1.2;
    }

    ensure_data_dir();
    snprintf(path,
             512,
             C_RESULTS_DIR "/zero_let_RC_n%d_%d_%lld_%s.svg",
             num_chains,
             num_repeats,
             random_seed,
             timestamp);
    f = fopen(path, "w");
    if (!f) {
        free(path);
        return NULL;
    }

    fprintf(f, "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1000\" height=\"700\" viewBox=\"0 0 1000 700\">\n");
    fprintf(f, "<rect width=\"100%%\" height=\"100%%\" fill=\"white\"/>\n");
    fprintf(f, "<text x=\"500\" y=\"35\" text-anchor=\"middle\" font-family=\"Arial\" font-size=\"22\">Normalized Runtime (R/C)</text>\n");
    fprintf(f, "<line x1=\"%.0f\" y1=\"%.0f\" x2=\"%.0f\" y2=\"%.0f\" stroke=\"#222\"/>\n", left, bottom, right, bottom);
    fprintf(f, "<line x1=\"%.0f\" y1=\"%.0f\" x2=\"%.0f\" y2=\"%.0f\" stroke=\"#222\"/>\n", left, top, left, bottom);
    write_log_axes(f, min_c, max_c, min_y, max_y, left, right, top, bottom);

    fprintf(f, "<text x=\"448\" y=\"675\" text-anchor=\"middle\" font-family=\"Arial\" font-size=\"16\">Complexity (C)</text>\n");
    fprintf(f, "<text x=\"24\" y=\"345\" text-anchor=\"middle\" font-family=\"Arial\" font-size=\"16\" transform=\"rotate(-90 24 345)\">R / C</text>\n");

    for (size_t i = 0; i < result_count; i++) {
        double c = (double)results[i].C;
        double y_value = results[i].R_over_C <= 0.0 ? 1e-12 : results[i].R_over_C;
        double x = left + (log10(c) - log10(min_c)) / (log10(max_c) - log10(min_c)) * (right - left);
        double y = bottom - (log10(y_value) - log10(min_y)) / (log10(max_y) - log10(min_y)) * (bottom - top);
        int style_idx = style_index_for_n(unique_n, unique_count, results[i].n);
        const char *color = colors[style_idx % (int)(sizeof(colors) / sizeof(colors[0]))];

        write_svg_marker(f, x, y, style_idx, color);
        fprintf(f, "<title>n=%d, C=%lld, R/C=%.6e</title>\n", results[i].n, results[i].C, results[i].R_over_C);
    }

    fprintf(f, "<text x=\"850\" y=\"95\" font-family=\"Arial\" font-size=\"15\" font-weight=\"bold\">Task chain length</text>\n");
    for (int i = 0; i < unique_count; i++) {
        double y = 125.0 + (double)i * 28.0;
        const char *color = colors[i % (int)(sizeof(colors) / sizeof(colors[0]))];

        write_svg_marker(f, 862.0, y - 5.0, i, color);
        fprintf(f, "<text x=\"882\" y=\"%.2f\" font-family=\"Arial\" font-size=\"14\">n=%d</text>\n", y, unique_n[i]);
    }

    fprintf(f, "</svg>\n");
    fclose(f);
    return path;
}

typedef struct {
    int num_chains;
    long long random_seed;
    long long processed;
    ExtremeResult *items;
    size_t used;
    size_t cap;
} ExtremeContext;

typedef struct {
    ExtremeContext *outer;
    ExtremeResult *slot;
    long long current_seed;
    long long idx;
} OffsetExtremeContext;

static void extreme_offset_cb(const long long *offsets, int n, void *ctx)
{
    OffsetExtremeContext *e = (OffsetExtremeContext *)ctx;
    AnalysisResult analysis;

    if (run_analysis_zero_let(n, e->slot->periods, offsets, offsets, 0.0, &analysis) != 0) {
        return;
    }

    if (analysis.stats.max < e->slot->min_value) {
        e->slot->min_value = analysis.stats.max;
        memcpy(e->slot->min_offsets, offsets, (size_t)n * sizeof(long long));
    }

    if (analysis.stats.max > e->slot->max_value) {
        e->slot->max_value = analysis.stats.max;
        memcpy(e->slot->max_offsets, offsets, (size_t)n * sizeof(long long));
    }

    e->idx++;
    free_analysis_result(&analysis);
}

static void period_extreme_cb(const long long *periods, int n, void *ctx)
{
    ExtremeContext *ec = (ExtremeContext *)ctx;
    ExtremeResult *slot;
    OffsetExtremeContext oc;

    if (ec->used == ec->cap) {
        size_t new_cap = ec->cap == 0 ? 16 : ec->cap * 2;
        ExtremeResult *new_items = (ExtremeResult *)realloc(ec->items, new_cap * sizeof(ExtremeResult));
        if (!new_items) {
            return;
        }
        memset(new_items + ec->cap, 0, (new_cap - ec->cap) * sizeof(ExtremeResult));
        ec->items = new_items;
        ec->cap = new_cap;
    }

    slot = &ec->items[ec->used++];
    slot->periods = (long long *)calloc((size_t)n, sizeof(long long));
    slot->min_offsets = (long long *)calloc((size_t)n, sizeof(long long));
    slot->max_offsets = (long long *)calloc((size_t)n, sizeof(long long));
    if (!slot->periods || !slot->min_offsets || !slot->max_offsets) {
        return;
    }

    memcpy(slot->periods, periods, (size_t)n * sizeof(long long));
    slot->min_value = DBL_MAX;
    slot->max_value = -DBL_MAX;
    slot->is_max_harmonic = isMaxHarmonic(periods, n);

    printf("[%lld] Processing Periods: [", ec->processed + 1);
    for (int i = 0; i < n; i++) {
        printf("%lld%s", periods[i], (i == n - 1) ? "" : ", ");
    }
    printf("]\n");

    oc.outer = ec;
    oc.slot = slot;
    oc.current_seed = ec->random_seed + ec->processed;
    oc.idx = 0;
    generate_all_read_combinations_zero(periods, n, extreme_offset_cb, &oc);
    ec->processed++;
}

ExtremeResult *run_evaluation_and_track_extremes(int num_chains,
                                                 long long random_seed,
                                                 long long perioddown,
                                                 long long periodup,
                                                 size_t *count)
{
    ExtremeContext ctx;
    long long total = count_period_combinations(perioddown, periodup, num_chains);

    if (!count) {
        return NULL;
    }

    memset(&ctx, 0, sizeof(ctx));
    ctx.num_chains = num_chains;
    ctx.random_seed = random_seed;

    srand((unsigned int)random_seed);
    printf("Starting evaluation for %lld period combinations...\n", total);
    generate_period_combinations(perioddown, periodup, num_chains, period_extreme_cb, &ctx);

    *count = ctx.used;
    return ctx.items;
}

char *output_zero_let_min_max_extremes(const char *timestamp,
                                       const ExtremeResult *results,
                                       size_t count,
                                       int num_chains,
                                       long long perioddown,
                                       long long periodup)
{
    char *path = (char *)calloc(512, sizeof(char));
    FILE *f;

    if (!path) {
        return NULL;
    }

    ensure_data_dir();
    snprintf(path,
             512,
             C_RESULTS_DIR "/data_zero_let_n%d_%lld_%lld_EXTREMES_%s.csv",
             num_chains,
             perioddown,
             periodup,
             timestamp);

    f = fopen(path, "w");
    if (!f) {
        free(path);
        return NULL;
    }

    fprintf(f,
            "period,minimum offset-free reaction time,offset of minimum (One of offsets can be obtained the minimum values),maximum offset-free reaction time,offset of maximum (One of offsets can be obtained the maximum values),between maximum and minimum,is max-harmonic\n");

    for (size_t i = 0; i < count; i++) {
        char periods[1024];
        char min_offsets[1024];
        char max_offsets[1024];

        format_array(periods, sizeof(periods), results[i].periods, num_chains);
        format_array(min_offsets, sizeof(min_offsets), results[i].min_offsets, num_chains);
        format_array(max_offsets, sizeof(max_offsets), results[i].max_offsets, num_chains);

        fprintf(f,
                "%s,%.3f,%s,%.3f,%s,%.3f,%d\n",
                periods,
                results[i].min_value,
                min_offsets,
                results[i].max_value,
                max_offsets,
                results[i].max_value - results[i].min_value,
                results[i].is_max_harmonic);
    }

    fclose(f);
    printf("Extreme values successfully saved to %s\n", path);
    return path;
}

void free_extreme_results(ExtremeResult *results, size_t count)
{
    if (!results) {
        return;
    }
    for (size_t i = 0; i < count; i++) {
        free(results[i].periods);
        free(results[i].min_offsets);
        free(results[i].max_offsets);
    }
    free(results);
}

#ifndef ZEROLET_EVALUATION_NO_MAIN
int main(int argc, char **argv)
{
    int num_limit = 3;
    int num_chains = 6;
    int num_repeats = 1;
    long long period_choices[] = {1, 2, 5, 10, 20, 50, 100, 200, 500, 1000};
    int n_choices = (int)(sizeof(period_choices) / sizeof(period_choices[0]));
    long long random_seed = (long long)time(NULL);
    char timestamp[64];
    size_t result_count = 0;
    ExperimentResult *results;
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

    if (argc > 4 || num_limit <= 0 || num_chains < num_limit || num_repeats <= 0) {
        fprintf(stderr, "Usage: %s [num_limit num_chains num_repeats]\n", argv[0]);
        fprintf(stderr, "Example: %s 3 6 1\n", argv[0]);
        return 1;
    }

    timestamp_from_seed(random_seed, timestamp, sizeof(timestamp));
    results = run_evaluation_zero_let(num_limit,
                                      num_chains,
                                      num_repeats,
                                      period_choices,
                                      n_choices,
                                      random_seed,
                                      &result_count);
    if (!results) {
        fprintf(stderr, "evaluation failed\n");
        return 1;
    }

    csvfile = output_zero_let(timestamp, num_chains, num_repeats, random_seed, results, result_count);
    if (csvfile) {
        char *plotfile = write_runtime_svg(results, result_count, num_chains, num_repeats, random_seed, timestamp);
        char *normalized_plotfile = write_normalized_runtime_svg(results, result_count, num_chains, num_repeats, random_seed, timestamp);
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

    for (size_t i = 0; i < result_count; i++) {
        free_experiment_result(&results[i]);
    }
    free(results);
    return 0;
}
#endif
