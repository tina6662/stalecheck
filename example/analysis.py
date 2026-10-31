"""Toy study: does sleep predict exam score? Every reported number goes through track()."""

import csv
import math
import statistics
from pathlib import Path

from stalecheck import track

EXCLUDE_FAILED_ATTENTION_CHECK = False  # the demo flips this to True

rows = list(csv.DictReader(open(Path(__file__).with_name("data.csv"))))
if EXCLUDE_FAILED_ATTENTION_CHECK:
    rows = [r for r in rows if r["passed_attention_check"] == "1"]

sleep = [float(r["sleep_hours"]) for r in rows]
score = [float(r["exam_score"]) for r in rows]

n = track("n", len(rows))
r = track("r_sleep_score", statistics.correlation(sleep, score))
slope = track("slope", statistics.linear_regression(sleep, score).slope)
df = track("df", n - 2)
t = r * math.sqrt(df / (1 - r * r))
track("t_stat", t)
track("mean_score", statistics.mean(score))
track("share_over_7h", sum(s >= 7 for s in sleep) / n)

print(f"n={n} r={r:.3f} slope={slope:.2f} t={t:.2f}")
