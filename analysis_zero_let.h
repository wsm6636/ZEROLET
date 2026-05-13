#ifndef ANALYSIS_ZERO_LET_H
#define ANALYSIS_ZERO_LET_H

#include <stddef.h>

typedef struct {
    int id;
    char event_type[6];
    long long period;
    long long offset;
    double maxjitter;
    double random_jitter;
} Event;

typedef struct {
    int id;
    Event read_event;
    Event write_event;
    long long period;
    long long offset;
} Task;

typedef struct {
    double latency;
    long long count;
} HistogramItem;

typedef struct {
    double min;
    double max;
    double mean;
    double std;
} LatencyStats;

typedef struct {
    HistogramItem *histogram;
    size_t histogram_len;
    double *latency_list;
    size_t latency_len;
    long long H;
    LatencyStats stats;
} AnalysisResult;

long long zerolet_gcd(long long a, long long b);
long long zerolet_lcm(long long a, long long b);
long long zerolet_lcm_list(const long long *numbers, int n);

double event_get_trigger_time(Event *event, long long j);
Task *generate_events_tasks(int num_tasks,
                            const long long *periods,
                            const long long *read_offsets,
                            const long long *write_offsets,
                            double per_jitter);

long long task_read_time(const Task *task, long long k);
long long task_write_time(const Task *task, long long k);

double compute_chain_latency_from_z(double z, const Task *tasks, int num_tasks);
int compute_latency_histogram(const Task *tasks,
                              int num_tasks,
                              HistogramItem **histogram,
                              size_t *histogram_len,
                              double **latency_list,
                              size_t *latency_len,
                              long long *H);
int compute_latency_stats(const HistogramItem *histogram,
                          size_t histogram_len,
                          long long total_count,
                          LatencyStats *stats);

int run_analysis_zero_let(int num_tasks,
                          const long long *periods,
                          const long long *read_offsets,
                          const long long *write_offsets,
                          double per_jitter,
                          AnalysisResult *result);
void free_analysis_result(AnalysisResult *result);

#endif
