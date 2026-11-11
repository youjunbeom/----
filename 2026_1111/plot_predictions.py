import csv
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).parent
PREDICTIONS_PATH = BASE_DIR / "predictions.csv"
OUTPUT_PATH = BASE_DIR / "prediction_week.png"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S%z"


def main():
    with PREDICTIONS_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError(f"No prediction rows found in {PREDICTIONS_PATH}")

    for row in rows:
        row["target_datetime"] = datetime.strptime(
            row["target_time_kst"], DATE_FORMAT
        )
        for field in (
            "actual_wind_speed_ms",
            "current_wind_persistence_ms",
            "linear_regression_prediction_ms",
            "random_forest_prediction_ms",
        ):
            row[field] = float(row[field])

    rows.sort(key=lambda row: row["target_datetime"])
    month_rows = [
        row
        for row in rows
        if row["target_datetime"].year == 2024
        and row["target_datetime"].month == 12
    ]
    week_start = datetime.fromisoformat("2024-12-01T00:00:00+09:00")
    week_end = datetime.fromisoformat("2024-12-08T00:00:00+09:00")
    week_rows = [
        row
        for row in month_rows
        if week_start <= row["target_datetime"] < week_end
    ]
    if not month_rows:
        raise ValueError("No December 2024 prediction rows found.")
    if not week_rows:
        raise ValueError("No prediction rows found for December 1-7, 2024.")

    fig, axis = plt.subplots(figsize=(13, 6))
    times = [row["target_datetime"] for row in week_rows]
    axis.plot(
        times,
        [row["actual_wind_speed_ms"] for row in week_rows],
        color="black",
        label="Actual",
        linewidth=1.5,
    )
    axis.plot(
        times,
        [row["current_wind_persistence_ms"] for row in week_rows],
        color="gray",
        linestyle="--",
        label="Current wind persistence",
        linewidth=1.3,
    )
    axis.plot(
        times,
        [row["linear_regression_prediction_ms"] for row in week_rows],
        color="blue",
        label="Linear regression",
        linewidth=1.3,
    )
    axis.plot(
        times,
        [row["random_forest_prediction_ms"] for row in week_rows],
        color="green",
        label="Random forest",
        linewidth=1.3,
    )
    axis.set_xlabel("Target time (KST)")
    axis.set_ylabel("Wind speed (m/s)")
    axis.set_title("Wind speed predictions: December 1-7, 2024")
    axis.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 12]))
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
    axis.set_xlim(times[0], times[-1])
    fig.autofmt_xdate()
    axis.legend()
    axis.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUTPUT_PATH, dpi=150)
    plt.close(fig)

    def mae(field):
        return sum(
            abs(row["actual_wind_speed_ms"] - row[field]) for row in month_rows
        ) / len(month_rows)

    print(f"그래프 행수 (12월 1일 00시~7일 23시): {len(week_rows)}")
    print(
        "그래프 대상 시각: "
        f"{week_rows[0]['target_datetime'].isoformat()} ~ "
        f"{week_rows[-1]['target_datetime'].isoformat()}"
    )
    print(f"12월 전체 평가 행수: {len(month_rows)}")
    print(f"12월 전체 현재 풍속 유지 MAE: {mae('current_wind_persistence_ms'):.6f} m/s")
    print(f"12월 전체 선형 회귀 MAE: {mae('linear_regression_prediction_ms'):.6f} m/s")
    print(f"12월 전체 랜덤 포레스트 MAE: {mae('random_forest_prediction_ms'):.6f} m/s")
    print(f"그래프 저장 위치: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
