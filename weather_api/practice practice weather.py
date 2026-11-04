import csv
from datetime import datetime, timedelta
from pathlib import Path

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError as error:
    if error.name != "matplotlib":
        raise
    raise SystemExit(
        "필요한 패키지 matplotlib가 없습니다. "
        "터미널에서 'python -m pip install -r requirements.txt'를 실행하세요."
    ) from error


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
CSV_PATH = SCRIPT_DIRECTORY / "practice_weather.csv"
REFERENCE_CSV_PATH = SCRIPT_DIRECTORY / "weather.csv"
IMAGE_PATH = SCRIPT_DIRECTORY / "practice_weather.png"


def load_weather(csv_path: Path) -> list[tuple[datetime, float | None]]:
    """CSV에서 시각과 기온을 읽고 시각순으로 정렬한다."""
    observations: list[tuple[datetime, float | None]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required_columns = {"datetime", "temperature_C"}
        if reader.fieldnames is None or not required_columns.issubset(reader.fieldnames):
            raise ValueError("CSV에 datetime 및 temperature_C 열이 필요합니다.")

        for line_number, row in enumerate(reader, start=2):
            raw_time = (row.get("datetime") or "").strip()
            raw_temperature = (row.get("temperature_C") or "").strip()
            if not raw_time:
                raise ValueError(f"CSV {line_number}행의 datetime 값이 비어 있습니다.")
            try:
                timestamp = datetime.fromisoformat(raw_time)
            except ValueError as error:
                raise ValueError(f"CSV {line_number}행의 datetime 형식이 올바르지 않습니다.") from error

            if raw_temperature:
                try:
                    temperature = float(raw_temperature)
                except ValueError as error:
                    raise ValueError(f"CSV {line_number}행의 temperature_C가 숫자가 아닙니다.") from error
            else:
                temperature = None
            observations.append((timestamp, temperature))

    if not observations:
        raise ValueError("CSV에 기상 자료가 없습니다.")

    observations.sort(key=lambda observation: observation[0])
    for previous, current in zip(observations, observations[1:]):
        if previous[0] == current[0]:
            raise ValueError(f"CSV에 같은 시각이 중복되어 있습니다: {current[0]}")
    return observations


def fill_missing_hours(
    observations: list[tuple[datetime, float | None]],
) -> tuple[list[datetime], list[float | None], list[datetime]]:
    """시작과 끝 사이를 시간 단위로 채우고, 없는 시각의 기온은 None으로 둔다."""
    if not observations:
        raise ValueError("시간축을 만들 관측 자료가 없습니다.")

    temperatures_by_time = dict(observations)
    start = observations[0][0]
    end = observations[-1][0]
    times: list[datetime] = []
    temperatures: list[float | None] = []
    missing_times: list[datetime] = []

    current = start
    while current <= end:
        times.append(current)
        if current in temperatures_by_time:
            temperatures.append(temperatures_by_time[current])
        else:
            temperatures.append(None)
            missing_times.append(current)
        current += timedelta(hours=1)
    return times, temperatures, missing_times


def save_temperature_plot(
    times: list[datetime],
    temperatures: list[float | None],
    image_path: Path,
) -> None:
    """시간-기온 선 그래프를 파일로 저장하고 화면에 표시한다."""
    figure, axis = plt.subplots(figsize=(12, 6))
    axis.plot(times, temperatures)
    axis.set_title("Temperature over time")
    axis.set_xlabel("Time (KST)")
    axis.set_ylabel("Temperature (°C)")
    figure.autofmt_xdate()
    figure.tight_layout()
    figure.savefig(image_path, dpi=150)
    plt.show()
    plt.close(figure)


def compare_periods(reference_path: Path, new_path: Path) -> str:
    """기존 기간과 새 기간의 평균 기온을 비교해 한 문장으로 반환한다."""
    reference = load_weather(reference_path)
    new_period = load_weather(new_path)
    reference_values = [value for _, value in reference if value is not None]
    new_values = [value for _, value in new_period if value is not None]
    if not reference_values or not new_values:
        raise ValueError("두 기간 모두 기온 관측값이 있어야 평균을 비교할 수 있습니다.")

    reference_mean = sum(reference_values) / len(reference_values)
    new_mean = sum(new_values) / len(new_values)
    difference = abs(new_mean - reference_mean)
    reference_dates = f"{reference[0][0]:%Y-%m-%d}~{reference[-1][0]:%Y-%m-%d}"
    new_dates = f"{new_period[0][0]:%Y-%m-%d}~{new_period[-1][0]:%Y-%m-%d}"
    if difference < 0.05:
        comparison = "평균 기온 차이가 거의 없습니다."
    elif new_mean > reference_mean:
        comparison = f"새 기간 평균 기온이 {difference:.1f}°C 높았습니다."
    else:
        comparison = f"새 기간 평균 기온이 {difference:.1f}°C 낮았습니다."
    return (
        f"{new_dates} 기간 평균 기온은 {new_mean:.1f}°C로, "
        f"{reference_dates} 기간({reference_mean:.1f}°C)보다 {comparison}"
    )


def main() -> None:
    """같은 폴더의 CSV를 읽고 누락 시각을 보고한 뒤 그래프를 만든다."""
    observations = load_weather(CSV_PATH)
    times, temperatures, missing_times = fill_missing_hours(observations)
    save_temperature_plot(times, temperatures, IMAGE_PATH)
    comparison = compare_periods(REFERENCE_CSV_PATH, CSV_PATH)

    print(f"관측 행 수: {len(observations)}")
    print(f"시간축 행 수(1시간 간격): {len(times)}")
    print(f"누락 시각 수: {len(missing_times)}")
    if missing_times:
        print("누락 시각:")
        for missing_time in missing_times:
            print(f"  {missing_time:%Y-%m-%d %H:%M:%S}")
    print(f"그래프 저장 위치: {IMAGE_PATH}")
    print(f"기간 차이: {comparison}")


if __name__ == "__main__":
    main()
