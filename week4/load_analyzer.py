"""load_bad.csv를 검증하고 하중 및 응력 결과를 저장합니다."""

import csv
import math
from pathlib import Path


CSV_PATH = Path(__file__).with_name("load_bad.csv")
DOWNLOADS_CSV_PATH = Path.home() / "Downloads" / "load_bad.csv"
area_mm2 = 100


def main():
    csv_path = CSV_PATH if CSV_PATH.exists() else DOWNLOADS_CSV_PATH
    result_path = csv_path.with_name("load_result.csv")
    plot_path = csv_path.with_name("stress_plot.png")
    try:
        with csv_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            required_columns = {"time_s", "force_N"}
            if reader.fieldnames is None or not required_columns.issubset(reader.fieldnames):
                raise ValueError("CSV 열 이름은 time_s와 force_N이어야 합니다.")

            fieldnames = list(reader.fieldnames)
            if "stress_MPa" not in fieldnames:
                fieldnames.append("stress_MPa")

            rows = []
            excluded_rows = 0
            for row in reader:
                row_number = reader.line_num
                invalid_values = []
                parsed_values = {}
                for column in ("time_s", "force_N"):
                    raw_value = row.get(column)
                    try:
                        parsed_value = float(raw_value.strip())
                        if not math.isfinite(parsed_value):
                            raise ValueError
                        parsed_values[column] = parsed_value
                    except (AttributeError, ValueError):
                        shown_value = "(빈칸)" if raw_value is None or not raw_value.strip() else raw_value
                        invalid_values.append((column, shown_value))

                if invalid_values:
                    excluded_rows += 1
                    for column, value in invalid_values:
                        print(f"제외: 원본 CSV {row_number}행, {column} 값={value!r}")
                    continue

                time_s = parsed_values["time_s"]
                force_n = parsed_values["force_N"]
                row["time_s"] = time_s
                row["force_N"] = force_n
                row["stress_MPa"] = force_n / area_mm2
                rows.append(row)

        if not rows:
            print(f"유효한 데이터가 없습니다. 계산과 파일 저장을 중단합니다. 제외한 행수: {excluded_rows}개")
            return

        with result_path.open("w", newline="", encoding="utf-8") as result_file:
            writer = csv.DictWriter(result_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    except (OSError, ValueError) as error:
        print(f"오류: {error}")
        return

    maximum_force_row = max(rows, key=lambda row: float(row["force_N"]))
    maximum_stress_row = max(rows, key=lambda row: float(row["stress_MPa"]))
    print(f"유효한 데이터 수: {len(rows)}개")
    print(f"제외한 행수: {excluded_rows}개")
    print(f"최대 하중: {float(maximum_force_row['force_N']):g} N")
    print(f"최대 하중 시각: {float(maximum_force_row['time_s']):g} s")
    print(f"최대 응력: {maximum_stress_row['stress_MPa']:g} MPa")
    print(f"최대 응력 시각: {float(maximum_stress_row['time_s']):g} s")
    print(f"결과 파일: {result_path.name}")

    try:
        import matplotlib.pyplot as plt  # type: ignore[import-not-found]

        times_s = [float(row["time_s"]) for row in rows]
        stresses_mpa = [row["stress_MPa"] for row in rows]
        plt.plot(times_s, stresses_mpa, marker="o", linestyle="-")
        plt.xlabel("Time (s)")
        plt.ylabel("Stress (MPa)")
        plt.savefig(plot_path)
        plt.close()
        print(f"그래프 파일: {plot_path.name}")
    except ImportError:
        print("오류: 그래프 저장에는 matplotlib가 필요합니다. pip install matplotlib")
    except OSError as error:
        new_func(error)

def new_func(error):
    print(f"그래프 저장 오류: {error}")


if __name__ == "__main__":
    main()
