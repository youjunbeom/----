import csv
import math
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path


DATASET_PATH = Path(__file__).with_name("wind_dataset.csv")
PREDICTIONS_PATH = Path(__file__).with_name("classification_predictions.csv")
SCORES_PATH = Path(__file__).with_name("classification_scores.csv")
THRESHOLD_MS = 4.0
LOGISTIC_THRESHOLD_50 = 0.50
LOGISTIC_THRESHOLD_20 = 0.20
TRAIN_START = datetime(2023, 1, 1)
EVALUATION_START = datetime(2024, 12, 1)
AFTER_EVALUATION = datetime(2025, 1, 1)
FEATURE_COLUMNS = (
    "current_wind_speed_ms",
    "current_temperature_C",
    "current_humidity_pct",
    "wind_speed_1h_ago_ms",
    "wind_speed_2h_ago_ms",
)
PREDICTION_COLUMNS = (
    "prediction_time",
    "target_time",
    "actual_wind_speed_ms",
    "actual_label",
    "current_wind_speed_ms",
    "always_zero_prediction",
    "current_speed_threshold_prediction",
    "logistic_regression_gale_probability",
    "logistic_regression_prediction",
    "logistic_regression_prediction_020",
)
SCORE_COLUMNS = (
    "method",
    "evaluation_rows",
    "actual_gales",
    "hits",
    "misses",
    "false_alarms",
    "correct_rejections",
    "accuracy",
    "gale_precision",
    "gale_recall",
)
PREDICTION_METHODS = (
    ("항상 0", "always_zero_prediction"),
    ("현재 풍속 ≥ 4.0 m/s", "current_speed_threshold_prediction"),
    ("로지스틱 회귀 (0.50)", "logistic_regression_prediction"),
    ("로지스틱 회귀 (0.20)", "logistic_regression_prediction_020"),
)


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def _standardize(
    train_features: list[list[float]], evaluation_features: list[list[float]]
) -> tuple[list[list[float]], list[list[float]]]:
    means = [
        sum(row[index] for row in train_features) / len(train_features)
        for index in range(len(FEATURE_COLUMNS))
    ]
    scales = []
    for index, mean in enumerate(means):
        variance = sum((row[index] - mean) ** 2 for row in train_features) / len(
            train_features
        )
        scales.append(math.sqrt(variance) or 1.0)

    def transform(rows: list[list[float]]) -> list[list[float]]:
        return [
            [(value - mean) / scale for value, mean, scale in zip(row, means, scales)]
            for row in rows
        ]

    return transform(train_features), transform(evaluation_features)


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [matrix[row][:] + [vector[row]] for row in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ArithmeticError("로지스틱 회귀의 최적화 행렬을 풀 수 없습니다.")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]

        divisor = augmented[column][column]
        for index in range(column, size + 1):
            augmented[column][index] /= divisor
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            for index in range(column, size + 1):
                augmented[row][index] -= factor * augmented[column][index]

    return [augmented[row][size] for row in range(size)]


def _fit_logistic_regression(
    features: list[list[float]], labels: list[int]
) -> list[float]:
    dimension = len(FEATURE_COLUMNS) + 1
    design = [[1.0, *row] for row in features]
    weights = [0.0] * dimension

    def objective(candidate: list[float]) -> float:
        loss = 0.5 * sum(value * value for value in candidate[1:])
        for row, label in zip(design, labels):
            score = sum(weight * value for weight, value in zip(candidate, row))
            loss += (
                max(score, 0.0)
                - label * score
                + math.log1p(math.exp(-abs(score)))
            )
        return loss

    for _ in range(100):
        gradient = [0.0] * dimension
        hessian = [[0.0] * dimension for _ in range(dimension)]
        for row, label in zip(design, labels):
            score = sum(weight * value for weight, value in zip(weights, row))
            probability = _sigmoid(score)
            residual = probability - label
            curvature = probability * (1.0 - probability)
            for first in range(dimension):
                gradient[first] += residual * row[first]
                for second in range(dimension):
                    hessian[first][second] += (
                        curvature * row[first] * row[second]
                    )

        for index in range(1, dimension):
            gradient[index] += weights[index]
            hessian[index][index] += 1.0
        if max(abs(value) for value in gradient) < 1e-6:
            return weights

        step = _solve_linear_system(hessian, gradient)
        directional_derivative = sum(
            value * delta for value, delta in zip(gradient, step)
        )
        current_loss = objective(weights)
        step_size = 1.0
        while step_size > 1e-8:
            candidate = [
                weight - step_size * delta
                for weight, delta in zip(weights, step)
            ]
            if (
                objective(candidate)
                <= current_loss - 1e-4 * step_size * directional_derivative
            ):
                weights = candidate
                break
            step_size *= 0.5
        else:
            raise ArithmeticError("로지스틱 회귀 최적화가 수렴하지 않았습니다.")

        if max(abs(step_size * value) for value in step) < 1e-9:
            return weights

    raise ArithmeticError("로지스틱 회귀가 최대 반복 횟수 안에 수렴하지 않았습니다.")


def main() -> None:
    with DATASET_PATH.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError(f"{DATASET_PATH.name}에 헤더가 없습니다.")

        wind_column = next(
            (
                column
                for column in ("wind_next1h", "actual_wind_speed_ms")
                if column in reader.fieldnames
            ),
            None,
        )
        required_columns = {"prediction_time", "target_time", *FEATURE_COLUMNS}
        missing_columns = required_columns.difference(reader.fieldnames)
        if missing_columns:
            raise ValueError(f"필수 열이 없습니다: {', '.join(sorted(missing_columns))}")
        if wind_column is None:
            raise ValueError(
                "풍속 열이 없습니다. wind_next1h 또는 actual_wind_speed_ms가 필요합니다."
            )

        train_rows = []
        evaluation_rows = []
        train_features = []
        evaluation_features = []
        train_labels = []
        previous_prediction_time = None
        previous_target_time = None

        for line_number, row in enumerate(reader, start=2):
            try:
                prediction_time = datetime.strptime(
                    row["prediction_time"], "%Y-%m-%d %H:%M:%S"
                )
                target_time = datetime.strptime(row["target_time"], "%Y-%m-%d %H:%M:%S")
                wind_speed = float(row[wind_column])
                features = [float(row[column]) for column in FEATURE_COLUMNS]
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"{line_number}행의 시각, 풍속 또는 입력 특성 값이 잘못되었습니다."
                ) from error

            if not math.isfinite(wind_speed):
                raise ValueError(f"{line_number}행의 풍속 값이 유한한 숫자가 아닙니다.")
            if not all(math.isfinite(value) for value in features):
                raise ValueError(f"{line_number}행의 입력 특성 값이 유한한 숫자가 아닙니다.")
            if target_time - prediction_time != timedelta(hours=1):
                raise ValueError(
                    f"{line_number}행의 prediction_time과 target_time 간격이 "
                    "정확히 1시간이 아닙니다."
                )
            if (
                previous_prediction_time is not None
                and prediction_time <= previous_prediction_time
            ):
                raise ValueError(f"{line_number}행에서 prediction_time 시간순이 깨졌습니다.")
            if previous_target_time is not None and target_time <= previous_target_time:
                raise ValueError(f"{line_number}행에서 target_time 시간순이 깨졌습니다.")

            previous_prediction_time = prediction_time
            previous_target_time = target_time

            if not (TRAIN_START <= target_time < AFTER_EVALUATION):
                continue

            row["label"] = str(int(wind_speed >= THRESHOLD_MS))
            if target_time < EVALUATION_START:
                train_rows.append(row)
                train_features.append(features)
                train_labels.append(int(row["label"]))
            else:
                evaluation_rows.append(row)
                evaluation_features.append(features)

    if not train_rows or not evaluation_rows:
        raise ValueError("학습 또는 평가 기간에 해당하는 행이 없습니다.")

    standardized_train, standardized_evaluation = _standardize(
        train_features, evaluation_features
    )
    weights = _fit_logistic_regression(standardized_train, train_labels)
    gale_probabilities = [
        _sigmoid(
            weights[0]
            + sum(weight * value for weight, value in zip(weights[1:], row))
        )
        for row in standardized_evaluation
    ]

    predictions = []
    for row, probability in zip(evaluation_rows, gale_probabilities):
        current_wind_speed = float(row["current_wind_speed_ms"])
        predictions.append(
            {
                "prediction_time": row["prediction_time"],
                "target_time": row["target_time"],
                "actual_wind_speed_ms": row[wind_column],
                "actual_label": row["label"],
                "current_wind_speed_ms": row["current_wind_speed_ms"],
                "always_zero_prediction": 0,
                "current_speed_threshold_prediction": int(
                    current_wind_speed >= THRESHOLD_MS
                ),
                "logistic_regression_gale_probability": f"{probability:.6f}",
                "logistic_regression_prediction": int(
                    probability >= LOGISTIC_THRESHOLD_50
                ),
                "logistic_regression_prediction_020": int(
                    probability >= LOGISTIC_THRESHOLD_20
                ),
            }
        )

    with PREDICTIONS_PATH.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=PREDICTION_COLUMNS)
        writer.writeheader()
        writer.writerows(predictions)

    evaluation_keys = [
        (row["prediction_time"], row["target_time"]) for row in predictions
    ]
    if len(set(evaluation_keys)) != len(predictions):
        raise ValueError("평가 데이터에 중복된 시각 행이 있습니다.")
    actual_labels = [int(row["actual_label"]) for row in predictions]
    actual_gales = sum(actual_labels)
    score_rows = []
    for method, prediction_column in PREDICTION_METHODS:
        predicted_labels = [int(row[prediction_column]) for row in predictions]
        hits = misses = false_alarms = correct_rejections = 0
        for actual, predicted in zip(actual_labels, predicted_labels):
            if actual == 1 and predicted == 1:
                hits += 1
            elif actual == 1:
                misses += 1
            elif predicted == 1:
                false_alarms += 1
            else:
                correct_rejections += 1
        if hits + misses + false_alarms + correct_rejections != len(predictions):
            raise ValueError(f"{method}의 분류 건수가 평가 행수와 일치하지 않습니다.")
        predicted_gales = hits + false_alarms
        accuracy = (hits + correct_rejections) / len(predictions)
        precision = hits / predicted_gales if predicted_gales else None
        recall = hits / actual_gales if actual_gales else None
        score_rows.append(
            {
                "method": method,
                "evaluation_rows": len(predictions),
                "actual_gales": actual_gales,
                "hits": hits,
                "misses": misses,
                "false_alarms": false_alarms,
                "correct_rejections": correct_rejections,
                "accuracy": f"{accuracy:.6f}",
                "gale_precision": (
                    f"{precision:.6f}" if precision is not None else "해당 없음"
                ),
                "gale_recall": (
                    f"{recall:.6f}" if recall is not None else "해당 없음"
                ),
            }
        )

    with SCORES_PATH.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=SCORE_COLUMNS)
        writer.writeheader()
        writer.writerows(score_rows)

    print(f"풍속 열: {wind_column} (KST 기준)")
    for name, rows in (("학습", train_rows), ("평가", evaluation_rows)):
        counts = Counter(row["label"] for row in rows)
        print(f"{name} 기간 전체 행수: {len(rows)}")
        print(f"{name} 기간 정답 0 개수: {counts['0']}")
        print(f"{name} 기간 정답 1 개수: {counts['1']}")

    print(f"표준화와 로지스틱 회귀 학습 행수: {len(train_features)}")
    print(f"클래스 가중치: 사용 안 함")
    print(f"예측 CSV 저장: {PREDICTIONS_PATH.name} ({len(predictions)}행)")
    print("예측 CSV 첫 5행:")
    with PREDICTIONS_PATH.open(encoding="utf-8-sig", newline="") as file:
        for row in list(csv.DictReader(file))[:5]:
            print(row)

    print(f"모든 방법 공통 평가행: {len(evaluation_keys)}행 (시각 중복 없음)")
    print(f"실제 강풍 행수: {actual_gales}")
    print(f"비교 결과 저장: {SCORES_PATH.name}")
    print(
        "방법 | 적중 | 놓침 | 오경보 | 정상판정 | 정확도 | 강풍 정밀도 | 강풍 재현율"
    )
    for score in score_rows:
        accuracy = float(score["accuracy"]) * 100
        precision = score["gale_precision"]
        if precision != "해당 없음":
            precision = f"{float(precision) * 100:.2f}%"
        recall = score["gale_recall"]
        if recall != "해당 없음":
            recall = f"{float(recall) * 100:.2f}%"
        print(
            f"{score['method']} | {score['hits']} | {score['misses']} | "
            f"{score['false_alarms']} | {score['correct_rejections']} | "
            f"{accuracy:.2f}% | {precision} | {recall}"
        )


if __name__ == "__main__":
    main()
