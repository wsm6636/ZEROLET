#include "analysis_zero_let.h"

#include <float.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef ZEROLET_BUILD_MAIN
#define ZEROLET_BUILD_MAIN 0
#endif

static double round_to_digits(double value, int digits)
{
    double scale = pow(10.0, (double)digits);
    return round(value * scale) / scale;
}

static double round9(double value)
{
    return round_to_digits(value, 9);
}

long long zerolet_gcd(long long a, long long b)
{
    if (a < 0) {
        a = -a;
    }
    if (b < 0) {
        b = -b;
    }
    while (b != 0) {
        long long r = a % b;
        a = b;
        b = r;
    }
    return a;
}

long long zerolet_lcm(long long a, long long b)
{
    long long g;

    if (a == 0 || b == 0) {
        return 0;
    }

    g = zerolet_gcd(a, b);
    return llabs(a / g * b);
}

long long zerolet_lcm_list(const long long *numbers, int n)
{
    long long result = 1;

    for (int i = 0; i < n; i++) {
        result = zerolet_lcm(result, numbers[i]);
    }
    return result;
}

double event_get_trigger_time(Event *event, long long j)
{
    double unit = (double)rand() / ((double)RAND_MAX + 1.0);
    event->random_jitter = unit * event->maxjitter;
    return (double)j * (double)event->period + (double)event->offset + event->random_jitter;
}

Task *generate_events_tasks(int num_tasks,
                            const long long *periods,
                            const long long *read_offsets,
                            const long long *write_offsets,
                            double per_jitter)
{
    Task *tasks = (Task *)calloc((size_t)num_tasks, sizeof(Task));

    if (!tasks) {
        return NULL;
    }

    for (int i = 0; i < num_tasks; i++) {
        double maxjitter = per_jitter * (double)periods[i];

        tasks[i].id = i;
        tasks[i].period = periods[i];
        tasks[i].offset = read_offsets[i];

        tasks[i].read_event.id = i;
        strcpy(tasks[i].read_event.event_type, "read");
        tasks[i].read_event.period = periods[i];
        tasks[i].read_event.offset = read_offsets[i];
        tasks[i].read_event.maxjitter = maxjitter;
        tasks[i].read_event.random_jitter = 0.0;

        tasks[i].write_event.id = i;
        strcpy(tasks[i].write_event.event_type, "write");
        tasks[i].write_event.period = periods[i];
        tasks[i].write_event.offset = write_offsets[i];
        tasks[i].write_event.maxjitter = maxjitter;
        tasks[i].write_event.random_jitter = 0.0;
    }

    return tasks;
}

long long task_read_time(const Task *task, long long k)
{
    return task->read_event.offset + k * task->period;
}

long long task_write_time(const Task *task, long long k)
{
    return task->write_event.offset + k * task->period;
}

double compute_chain_latency_from_z(double z, const Task *tasks, int num_tasks)
{
    double current_time = z;

    for (int i = 0; i < num_tasks; i++) {
        double T = (double)tasks[i].period;
        double r = (double)tasks[i].read_event.offset;
        double w = (double)tasks[i].write_event.offset;
        long long k = (long long)ceil((current_time - r) / T);

        if (k < 0) {
            k = 0;
        }

        current_time = (double)k * T + w;
    }

    return current_time - z;
}

static int compare_histogram_item(const void *a, const void *b)
{
    const HistogramItem *x = (const HistogramItem *)a;
    const HistogramItem *y = (const HistogramItem *)b;

    if (x->latency < y->latency) {
        return -1;
    }
    if (x->latency > y->latency) {
        return 1;
    }
    return 0;
}

static int append_histogram_item(HistogramItem **items,
                                 size_t *len,
                                 size_t *cap,
                                 double latency)
{
    for (size_t i = 0; i < *len; i++) {
        if ((*items)[i].latency == latency) {
            (*items)[i].count++;
            return 0;
        }
    }

    if (*len == *cap) {
        size_t new_cap = (*cap == 0) ? 16 : (*cap * 2);
        HistogramItem *new_items = (HistogramItem *)realloc(*items, new_cap * sizeof(HistogramItem));

        if (!new_items) {
            return -1;
        }
        *items = new_items;
        *cap = new_cap;
    }

    (*items)[*len].latency = latency;
    (*items)[*len].count = 1;
    (*len)++;
    return 0;
}

int compute_latency_histogram(const Task *tasks,
                              int num_tasks,
                              HistogramItem **histogram,
                              size_t *histogram_len,
                              double **latency_list,
                              size_t *latency_len,
                              long long *H)
{
    long long *periods = NULL;
    long long max_offset;
    HistogramItem *items = NULL;
    size_t items_len = 0;
    size_t items_cap = 0;
    double *latencies = NULL;

    if (!tasks || num_tasks <= 0 || !histogram || !histogram_len || !latency_list || !latency_len || !H) {
        return -1;
    }

    periods = (long long *)malloc((size_t)num_tasks * sizeof(long long));
    if (!periods) {
        return -1;
    }

    max_offset = tasks[0].read_event.offset;
    for (int i = 0; i < num_tasks; i++) {
        periods[i] = tasks[i].period;
        if (tasks[i].read_event.offset > max_offset) {
            max_offset = tasks[i].read_event.offset;
        }
    }

    *H = zerolet_lcm_list(periods, num_tasks);
    free(periods);

    if (*H < 0 || (unsigned long long)*H > (unsigned long long)(SIZE_MAX / sizeof(double))) {
        return -1;
    }

    latencies = (double *)malloc((size_t)*H * sizeof(double));
    if (!latencies) {
        return -1;
    }

    for (long long z = max_offset; z < *H + max_offset; z++) {
        double latency = round9(compute_chain_latency_from_z((double)z, tasks, num_tasks));
        size_t idx = (size_t)(z - max_offset);

        latencies[idx] = latency;
        if (append_histogram_item(&items, &items_len, &items_cap, latency) != 0) {
            free(items);
            free(latencies);
            return -1;
        }
    }

    qsort(items, items_len, sizeof(HistogramItem), compare_histogram_item);

    *histogram = items;
    *histogram_len = items_len;
    *latency_list = latencies;
    *latency_len = (size_t)*H;
    return 0;
}

int compute_latency_stats(const HistogramItem *histogram,
                          size_t histogram_len,
                          long long total_count,
                          LatencyStats *stats)
{
    double mean = 0.0;
    double variance = 0.0;

    if (!histogram || histogram_len == 0 || total_count == 0 || !stats) {
        return -1;
    }

    for (size_t i = 0; i < histogram_len; i++) {
        mean += histogram[i].latency * (double)histogram[i].count;
    }
    mean /= (double)total_count;

    for (size_t i = 0; i < histogram_len; i++) {
        double diff = histogram[i].latency - mean;
        variance += (double)histogram[i].count * diff * diff;
    }
    variance /= (double)total_count;

    stats->min = round_to_digits(histogram[0].latency, 3);
    stats->max = round_to_digits(histogram[histogram_len - 1].latency, 3);
    stats->mean = round_to_digits(mean, 3);
    stats->std = round_to_digits(sqrt(variance), 3);
    return 0;
}

int run_analysis_zero_let(int num_tasks,
                          const long long *periods,
                          const long long *read_offsets,
                          const long long *write_offsets,
                          double per_jitter,
                          AnalysisResult *result)
{
    Task *tasks = NULL;
    int rc;

    if (!periods || !read_offsets || !write_offsets || !result || num_tasks <= 0) {
        return -1;
    }

    memset(result, 0, sizeof(*result));
    tasks = generate_events_tasks(num_tasks, periods, read_offsets, write_offsets, per_jitter);
    if (!tasks) {
        return -1;
    }

    rc = compute_latency_histogram(tasks,
                                   num_tasks,
                                   &result->histogram,
                                   &result->histogram_len,
                                   &result->latency_list,
                                   &result->latency_len,
                                   &result->H);
    free(tasks);

    if (rc != 0) {
        free_analysis_result(result);
        return -1;
    }

    if (compute_latency_stats(result->histogram, result->histogram_len, result->H, &result->stats) != 0) {
        free_analysis_result(result);
        return -1;
    }

    return 0;
}

void free_analysis_result(AnalysisResult *result)
{
    if (!result) {
        return;
    }
    free(result->histogram);
    free(result->latency_list);
    memset(result, 0, sizeof(*result));
}

#if ZEROLET_BUILD_MAIN
int main(void)
{
    long long periods[] = {15, 10, 12};
    long long read_offsets[] = {11, 18, 26};
    long long write_offsets[] = {11, 18, 26};
    AnalysisResult result;

    if (run_analysis_zero_let(3, periods, read_offsets, write_offsets, 0.0, &result) != 0) {
        fprintf(stderr, "analysis failed\n");
        return 1;
    }

    printf("Hyperperiod: %lld\n", result.H);
    printf("Latency stats: {'min': %.3f, 'max': %.3f, 'mean': %.3f, 'std': %.3f}\n",
           result.stats.min,
           result.stats.max,
           result.stats.mean,
           result.stats.std);

    free_analysis_result(&result);
    return 0;
}
#endif
