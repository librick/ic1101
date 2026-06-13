/*
 * sleep.c - minimal static sleep helper for the recovery environment.
 *
 * Waits the whole seconds given as argv[1] (default DEFAULT_SECS, clamped to
 * [MIN_SECS, MAX_SECS]) against an absolute deadline on the monotonic clock,
 * so the wait is bounded by the deadline and cannot drift, overshoot, or
 * stall regardless of signals or clock adjustments.
 */
#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define DEFAULT_SECS 30
#define MIN_SECS 10
#define MAX_SECS 120

int main(int argc, char **argv)
{
    long secs = DEFAULT_SECS;

    if (argc > 1) {
        char *end = NULL;
        errno = 0;
        long v = strtol(argv[1], &end, 10);

        if (errno == 0 && end != argv[1] && *end == '\0') {
            secs = v;
        } else {
            fprintf(stderr, "sleep: bad argument '%s', using %d\n",
                    argv[1], DEFAULT_SECS);
            secs = DEFAULT_SECS;
        }
    }

    if (secs < MIN_SECS) secs = MIN_SECS;
    if (secs > MAX_SECS) secs = MAX_SECS;

    fprintf(stderr, "sleep: waiting %ld second(s)\n", secs);

    /* bionic at this API level does not declare clock_nanosleep, so we wait
     * with nanosleep and recompute the remaining interval from a fixed
     * monotonic deadline on each pass. Monotonic means a wall-clock change
     * cannot move the deadline; recomputing each pass means an interruption
     * cannot drift or stall. The loop is bounded because monotonic time only
     * advances toward the deadline. */
    struct timespec deadline;
    if (clock_gettime(CLOCK_MONOTONIC, &deadline) != 0) {
        fprintf(stderr, "sleep: clock_gettime failed: %s\n", strerror(errno));
        return 1;
    }
    deadline.tv_sec += secs;

    for (;;) {
        struct timespec now;
        if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) {
            fprintf(stderr, "sleep: clock_gettime failed: %s\n", strerror(errno));
            return 1;
        }

        struct timespec rem;
        rem.tv_sec = deadline.tv_sec - now.tv_sec;
        rem.tv_nsec = deadline.tv_nsec - now.tv_nsec;
        if (rem.tv_nsec < 0) {
            rem.tv_sec -= 1;
            rem.tv_nsec += 1000000000L;
        }
        if (rem.tv_sec < 0) {
            break;  /* deadline reached */
        }

        if (nanosleep(&rem, NULL) == 0) {
            break;  /* full remaining interval elapsed */
        }
        if (errno != EINTR) {
            fprintf(stderr, "sleep: nanosleep failed: %s\n", strerror(errno));
            return 1;
        }
        /* interrupted: recompute against the same deadline and continue */
    }

    return 0;
}