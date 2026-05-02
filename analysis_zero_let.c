#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <time.h>

#define MAX_TASKS 10
#define MAX_RESULTS 20000

/* ---------- 工具 ---------- */

int gcd(int a, int b) {
    return b == 0 ? a : gcd(b, a % b);
}

int lcm(int a, int b) {
    return a / gcd(a, b) * b;
}

int lcm_list(int arr[], int n) {
    int res = 1;
    for (int i = 0; i < n; i++)
        res = lcm(res, arr[i]);
    return res;
}

/* ---------- 数据结构 ---------- */

typedef struct {
    double min;
    double max;
    double mean;
    double std;
} Stats;

typedef struct {
    int periods[MAX_TASKS];
    int offsets[MAX_TASKS];
    Stats stats;
} Record;

typedef struct {
    int periods[MAX_TASKS];
    Record min_rec;
    Record max_rec;
    int valid;
} PeriodEntry;

/* ---------- 核心计算 ---------- */

double compute_chain_latency(int z, int periods[], int offsets[], int n) {
    double current_time = z;

    for (int i = 0; i < n; i++) {
        int T = periods[i];
        int r = offsets[i];
        int w = offsets[i];

        int k = ceil((current_time - r) / (double)T);
        if (k < 0) k = 0;

        current_time = k * T + w;
    }

    return current_time - z;
}

void compute_stats(int periods[], int offsets[], int n, Stats *stats) {
    int H = lcm_list(periods, n);

    double sum = 0, sum_sq = 0;
    double min_lat = 1e9, max_lat = -1e9;

    int max_offset = 0;
    for (int i = 0; i < n; i++)
        if (offsets[i] > max_offset)
            max_offset = offsets[i];

    int count = 0;

    for (int z = max_offset; z < H + max_offset; z++) {
        double lat = compute_chain_latency(z, periods, offsets, n);

        // 对齐 Python round(lat, 9)
        lat = round(lat * 1e9) / 1e9;

        if (lat < min_lat) min_lat = lat;
        if (lat > max_lat) max_lat = lat;

        sum += lat;
        sum_sq += lat * lat;
        count++;
    }

    double mean = sum / count;
    double variance = sum_sq / count - mean * mean;

    stats->min = round(min_lat * 1000) / 1000.0;
    stats->max = round(max_lat * 1000) / 1000.0;
    stats->mean = round(mean * 1000) / 1000.0;
    stats->std = round(sqrt(variance) * 1000) / 1000.0;
}

/* ---------- harmonic ---------- */

int isMaxHarmonic(int periods[], int n) {
    int maxP = 0;
    for (int i = 0; i < n; i++)
        if (periods[i] > maxP) maxP = periods[i];

    for (int i = 0; i < n; i++)
        if (periods[i] == 0 || maxP % periods[i] != 0)
            return 0;

    return 1;
}

/* ---------- 全局 ---------- */

PeriodEntry results[MAX_RESULTS];
int result_count = 0;

/* ---------- 打印数组（CSV用） ---------- */

void print_array(FILE *fp, int arr[], int n) {
    fprintf(fp, "\"[");
    for (int i = 0; i < n; i++) {
        fprintf(fp, "%d", arr[i]);
        if (i != n - 1) fprintf(fp, ",");
    }
    fprintf(fp, "]\"");
}

/* ---------- offset 枚举 ---------- */

void evaluate_offsets(int periods[], int offsets[], int n, PeriodEntry *entry) {
    Stats stats;
    compute_stats(periods, offsets, n, &stats);

    if (!entry->valid || stats.max < entry->min_rec.stats.max) {
        memcpy(entry->min_rec.periods, periods, sizeof(int)*n);
        memcpy(entry->min_rec.offsets, offsets, sizeof(int)*n);
        entry->min_rec.stats = stats;
    }

    if (!entry->valid || stats.max > entry->max_rec.stats.max) {
        memcpy(entry->max_rec.periods, periods, sizeof(int)*n);
        memcpy(entry->max_rec.offsets, offsets, sizeof(int)*n);
        entry->max_rec.stats = stats;
    }

    entry->valid = 1;
}

void generate_offsets(int periods[], int n, int idx, int current[], PeriodEntry *entry) {
    if (idx == n) {
        evaluate_offsets(periods, current, n, entry);
        return;
    }

    int max_val = (idx == 0) ? 0 : periods[idx];

    for (int i = 0; i <= max_val; i++) {
        current[idx] = i;
        generate_offsets(periods, n, idx + 1, current, entry);
    }
}

/* ---------- period 枚举 ---------- */

void generate_periods(int perioddown, int periodup, int n, int idx, int current[]) {
    if (idx == n) {

        // 进度打印（通用）
        printf("Processing [");
        for (int i = 0; i < n; i++) {
            printf("%d", current[i]);
            if (i != n-1) printf(",");
        }
        printf("]\n");

        PeriodEntry entry = {0};
        memcpy(entry.periods, current, sizeof(int)*n);

        int offsets[MAX_TASKS];
        generate_offsets(current, n, 0, offsets, &entry);

        results[result_count++] = entry;
        return;
    }

    for (int p = perioddown; p <= periodup; p++) {
        current[idx] = p;
        generate_periods(perioddown, periodup, n, idx + 1, current);
    }
}

/* ---------- 排序 ---------- */

int compare_periods(const void *a, const void *b) {
    PeriodEntry *pa = (PeriodEntry*)a;
    PeriodEntry *pb = (PeriodEntry*)b;

    for (int i = 0; i < MAX_TASKS; i++) {
        if (pa->periods[i] != pb->periods[i])
            return pa->periods[i] - pb->periods[i];
    }
    return 0;
}

/* ---------- CSV 输出 ---------- */

void write_csv(int n, int perioddown, int periodup) {

    time_t t = time(NULL);
    struct tm *tm = localtime(&t);

    char filename[256];
    sprintf(filename,
        "data/data_zero_let_n%d_%d_%d_EXTREMES_%04d%02d%02d_%02d%02d%02d.csv",
        n, perioddown, periodup,
        tm->tm_year+1900, tm->tm_mon+1, tm->tm_mday,
        tm->tm_hour, tm->tm_min, tm->tm_sec);

    FILE *fp = fopen(filename, "w");

    fprintf(fp,
        "$T_i$ period,"
        "$L_Z^-$ minimum offset-free reaction time,"
        "$phase$ offsets min,"
        "$L_Z^+$ maximum offset-free reaction time,"
        "$phase$ offsets max,"
        "diff,"
        "is max-harmonic\n");

    qsort(results, result_count, sizeof(PeriodEntry), compare_periods);

    for (int i = 0; i < result_count; i++) {

        PeriodEntry *e = &results[i];

        double minv = e->min_rec.stats.max;
        double maxv = e->max_rec.stats.max;
        double diff = maxv - minv;

        print_array(fp, e->periods, n);
        fprintf(fp, ",");

        fprintf(fp, "%.3f,", minv);

        print_array(fp, e->min_rec.offsets, n);
        fprintf(fp, ",");

        fprintf(fp, "%.3f,", maxv);

        print_array(fp, e->max_rec.offsets, n);
        fprintf(fp, ",");

        fprintf(fp, "%.3f,", diff);

        fprintf(fp, "%d\n", isMaxHarmonic(e->periods, n));
    }

    fclose(fp);

    printf("Saved to %s\n", filename);
}

/* ---------- main ---------- */

int main() {

    int perioddown = 2;
    int periodup = 12;
    int num_chains = 3;  

    int periods[MAX_TASKS];

    generate_periods(perioddown, periodup, num_chains, 0, periods);

    write_csv(num_chains, perioddown, periodup);

    return 0;
}