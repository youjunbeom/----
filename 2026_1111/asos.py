import csv
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
SOURCE_PATH = Path(__file__).with_name("asos_108_2023_2024.csv")
OUTPUT_PATH = Path(__file__).with_name("wind_dataset.csv")
PREDICTIONS_PATH = Path(__file__).with_name("predictions.csv")
KST = timezone(timedelta(hours=9))
FEATURE_FIELDS = [
    "current_wind_speed_ms",
    "wind_speed_1h_ago_ms",
    "wind_speed_2h_ago_ms",
    "current_temperature_C",
    "current_humidity_pct",
]
OUTPUT_FIELDS = [
    "prediction_time",
    "target_time",
    "current_wind_speed_ms",
    "current_temperature_C",
    "current_humidity_pct",
    "wind_speed_1h_ago_ms",
    "wind_speed_2h_ago_ms",
    "actual_wind_speed_ms",
]
PREDICTION_FIELDS = [
    "prediction_time_kst",
    "target_time_kst",
    "actual_wind_speed_ms",
    "current_wind_persistence_ms",
    "linear_regression_prediction_ms",
    "random_forest_prediction_ms",
]


def fit_linear_regression(features, targets):
    feature_count = len(features[0])
    row_count = len(features)
    feature_means = [
        sum(row[index] for row in features) / row_count
        for index in range(feature_count)
    ]
    feature_scales = [
        math.sqrt(
            sum((row[index] - feature_means[index]) ** 2 for row in features)
            / row_count
        )
        for index in range(feature_count)
    ]
    if any(scale == 0 for scale in feature_scales):
        raise ValueError("A training feature has zero variance.")

    target_mean = sum(targets) / row_count
    standardized = [
        [
            (row[index] - feature_means[index]) / feature_scales[index]
            for index in range(feature_count)
        ]
        for row in features
    ]
    matrix = []
    for left in range(feature_count):
        matrix.append(
            [
                sum(row[left] * row[right] for row in standardized)
                for right in range(feature_count)
            ]
            + [
                sum(
                    row[left] * (target - target_mean)
                    for row, target in zip(standardized, targets)
                )
            ]
        )

    for pivot_index in range(feature_count):
        pivot_row = max(
            range(pivot_index, feature_count),
            key=lambda row_index: abs(matrix[row_index][pivot_index]),
        )
        if abs(matrix[pivot_row][pivot_index]) < 1e-12:
            raise ValueError("The training features do not determine a unique model.")
        matrix[pivot_index], matrix[pivot_row] = (
            matrix[pivot_row],
            matrix[pivot_index],
        )
        pivot = matrix[pivot_index][pivot_index]
        matrix[pivot_index] = [value / pivot for value in matrix[pivot_index]]
        for row_index in range(feature_count):
            if row_index == pivot_index:
                continue
            factor = matrix[row_index][pivot_index]
            matrix[row_index] = [
                value - factor * pivot_value
                for value, pivot_value in zip(
                    matrix[row_index], matrix[pivot_index]
                )
            ]

    coefficients = [matrix[index][-1] for index in range(feature_count)]
    return feature_means, feature_scales, target_mean, coefficients


def predict_linear_regression(model, features):
    feature_means, feature_scales, target_mean, coefficients = model
    return target_mean + sum(
        coefficient * (value - mean) / scale
        for value, mean, scale, coefficient in zip(
            features, feature_means, feature_scales, coefficients
        )
    )


def fit_random_forest(features, targets, n_estimators=100, max_depth=6,
                      min_samples_leaf=5, random_state=42):
    rng = random.Random(random_state)
    feature_count = len(features[0])
    max_features = max(1, math.isqrt(feature_count))
    forest = []

    def build_tree(indices, depth):
        mean = sum(targets[index] for index in indices) / len(indices)
        if depth >= max_depth or len(indices) < 2 * min_samples_leaf:
            return ("leaf", mean)

        best_split = None
        for feature_index in rng.sample(range(feature_count), max_features):
            ordered = sorted(indices, key=lambda index: features[index][feature_index])
            total_sum = sum(targets[index] for index in ordered)
            total_square_sum = sum(targets[index] ** 2 for index in ordered)
            left_sum = 0.0
            left_square_sum = 0.0

            for position in range(1, len(ordered)):
                target = targets[ordered[position - 1]]
                left_sum += target
                left_square_sum += target * target
                left_count = position
                right_count = len(ordered) - left_count
                if (
                    left_count < min_samples_leaf
                    or right_count < min_samples_leaf
                ):
                    continue
                if features[ordered[position - 1]][feature_index] == features[
                    ordered[position]
                ][feature_index]:
                    continue

                right_sum = total_sum - left_sum
                right_square_sum = total_square_sum - left_square_sum
                loss = (
                    left_square_sum - left_sum * left_sum / left_count
                    + right_square_sum - right_sum * right_sum / right_count
                )
                if best_split is None or loss < best_split[0]:
                    lower = features[ordered[position - 1]][feature_index]
                    upper = features[ordered[position]][feature_index]
                    best_split = (loss, feature_index, (lower + upper) / 2)

        if best_split is None:
            return ("leaf", mean)

        _, feature_index, threshold = best_split
        left_indices = [
            index for index in indices if features[index][feature_index] <= threshold
        ]
        right_indices = [
            index for index in indices if features[index][feature_index] > threshold
        ]
        if (
            len(left_indices) < min_samples_leaf
            or len(right_indices) < min_samples_leaf
        ):
            return ("leaf", mean)
        return (
            "split",
            feature_index,
            threshold,
            build_tree(left_indices, depth + 1),
            build_tree(right_indices, depth + 1),
        )

    for _ in range(n_estimators):
        bootstrap_indices = [
            rng.randrange(len(features)) for _ in range(len(features))
        ]
        forest.append(build_tree(bootstrap_indices, 0))
    return forest


def predict_random_forest(forest, features):
    def predict_tree(tree):
        if tree[0] == "leaf":
            return tree[1]
        _, feature_index, threshold, left, right = tree
        branch = left if features[feature_index] <= threshold else right
        return predict_tree(branch)

    return sum(predict_tree(tree) for tree in forest) / len(forest)


def main():
    with SOURCE_PATH.open("r", encoding="utf-8-sig", newline="") as source_file:
        reader = csv.DictReader(source_file)
        observations = {}
        for row in reader:
            timestamp = datetime.strptime(row["datetime"].strip(), TIMESTAMP_FORMAT)
            if timestamp in observations:
                raise ValueError(f"Duplicate observation time: {timestamp}")
            observations[timestamp] = row

    if not observations:
        raise ValueError(f"No observations found in {SOURCE_PATH}")

    first_time = min(observations)
    last_time = max(observations)
    aligned_times = []
    timestamp = first_time
    while timestamp <= last_time:
        aligned_times.append(timestamp)
        timestamp += timedelta(hours=1)

    samples = []
    for prediction_time in aligned_times:
        target_time = prediction_time + timedelta(hours=1)
        current = observations.get(prediction_time)
        one_hour_ago = observations.get(prediction_time - timedelta(hours=1))
        two_hours_ago = observations.get(prediction_time - timedelta(hours=2))
        target = observations.get(target_time)
        if not all((current, one_hour_ago, two_hours_ago, target)):
            continue

        values = [
            current["wind_speed_ms"],
            current["temperature_C"],
            current["humidity_pct"],
            one_hour_ago["wind_speed_ms"],
            two_hours_ago["wind_speed_ms"],
            target["wind_speed_ms"],
        ]
        if any(not (value or "").strip() for value in values):
            continue

        samples.append(
            {
                "prediction_time": prediction_time.strftime(TIMESTAMP_FORMAT),
                "target_time": target_time.strftime(TIMESTAMP_FORMAT),
                "current_wind_speed_ms": current["wind_speed_ms"],
                "current_temperature_C": current["temperature_C"],
                "current_humidity_pct": current["humidity_pct"],
                "wind_speed_1h_ago_ms": one_hour_ago["wind_speed_ms"],
                "wind_speed_2h_ago_ms": two_hours_ago["wind_speed_ms"],
                "actual_wind_speed_ms": target["wind_speed_ms"],
            }
        )

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(samples)

    chronological_samples = sorted(
        samples,
        key=lambda sample: datetime.strptime(
            sample["target_time"], TIMESTAMP_FORMAT
        ).replace(tzinfo=KST),
    )
    train_start = datetime(2023, 1, 1, tzinfo=KST)
    train_end = datetime(2024, 12, 1, tzinfo=KST)
    evaluation_start = train_end
    evaluation_end = datetime(2025, 1, 1, tzinfo=KST)

    def target_datetime(sample):
        return datetime.strptime(sample["target_time"], TIMESTAMP_FORMAT).replace(
            tzinfo=KST
        )

    def prediction_datetime(sample):
        return datetime.strptime(sample["prediction_time"], TIMESTAMP_FORMAT).replace(
            tzinfo=KST
        )

    training_rows = [
        sample
        for sample in chronological_samples
        if train_start <= target_datetime(sample) < train_end
    ]
    evaluation_rows = [
        sample
        for sample in chronological_samples
        if evaluation_start <= target_datetime(sample) < evaluation_end
    ]
    if not training_rows:
        raise ValueError("No rows found in the training period.")
    if not evaluation_rows:
        raise ValueError("No rows found in the December 2024 evaluation period.")

    training_features = [
        [float(sample[field]) for field in FEATURE_FIELDS] for sample in training_rows
    ]
    model = fit_linear_regression(
        training_features,
        [float(sample["actual_wind_speed_ms"]) for sample in training_rows],
    )
    evaluation_features = [
        [float(sample[field]) for field in FEATURE_FIELDS]
        for sample in evaluation_rows
    ]
    regression_predictions = [
        max(0.0, predict_linear_regression(model, features))
        for features in evaluation_features
    ]
    random_forest = fit_random_forest(
        training_features,
        [float(sample["actual_wind_speed_ms"]) for sample in training_rows],
        n_estimators=100,
        max_depth=6,
        min_samples_leaf=5,
        random_state=42,
    )
    forest_predictions = [
        max(0.0, predict_random_forest(random_forest, features))
        for features in evaluation_features
    ]
    actual_values = [
        float(sample["actual_wind_speed_ms"]) for sample in evaluation_rows
    ]
    persistence_predictions = [
        float(sample["current_wind_speed_ms"]) for sample in evaluation_rows
    ]

    prediction_rows = []
    for sample, actual, persistence, regression, forest_prediction in zip(
        evaluation_rows,
        actual_values,
        persistence_predictions,
        regression_predictions,
        forest_predictions,
    ):
        prediction_rows.append(
            {
                "prediction_time_kst": prediction_datetime(sample).isoformat(
                    sep=" "
                ),
                "target_time_kst": target_datetime(sample).isoformat(sep=" "),
                "actual_wind_speed_ms": actual,
                "current_wind_persistence_ms": persistence,
                "linear_regression_prediction_ms": regression,
                "random_forest_prediction_ms": forest_prediction,
            }
        )
    with PREDICTIONS_PATH.open("w", encoding="utf-8", newline="") as predictions_file:
        writer = csv.DictWriter(predictions_file, fieldnames=PREDICTION_FIELDS)
        writer.writeheader()
        writer.writerows(prediction_rows)

    persistence_mae = sum(
        abs(actual - prediction)
        for actual, prediction in zip(actual_values, persistence_predictions)
    ) / len(actual_values)
    regression_mae = sum(
        abs(actual - prediction)
        for actual, prediction in zip(actual_values, regression_predictions)
    ) / len(actual_values)
    forest_mae = sum(
        abs(actual - prediction)
        for actual, prediction in zip(actual_values, forest_predictions)
    ) / len(actual_values)

    print(f"시간 간격 정렬 후 행수: {len(aligned_times)}")
    print(f"저장된 데이터 행수: {len(samples)}")
    print(f"학습 행수 (정답 시각 기준 2023-01~2024-11): {len(training_rows)}")
    print(f"평가 행수 (정답 시각 기준 2024-12): {len(evaluation_rows)}")
    print(f"현재 풍속 유지 MAE: {persistence_mae:.6f} m/s")
    print(f"선형 회귀 MAE (음수 예측은 0으로 보정): {regression_mae:.6f} m/s")
    print(
        "랜덤 포레스트 MAE (100개 트리, 깊이 6, 리프 최소 표본 5, seed=42): "
        f"{forest_mae:.6f} m/s"
    )
    print(
        "랜덤 포레스트 MAE 감소량: "
        f"현재 풍속 유지 대비 {persistence_mae - forest_mae:.6f} m/s, "
        f"선형 회귀 대비 {regression_mae - forest_mae:.6f} m/s"
    )
    print("첫 평가 결과:")
    print(",".join(PREDICTION_FIELDS))
    print(",".join(str(prediction_rows[0][field]) for field in PREDICTION_FIELDS))
    print(f"예측 결과 저장 위치: {PREDICTIONS_PATH}")


if __name__ == "__main__":
    main()