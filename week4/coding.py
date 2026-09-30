"""원형 봉의 축응력 계산기.

축응력 공식:
    A = pi * d^2 / 4
    sigma = P / A

P: 축력 [kN]
d: 원형 봉의 직경 [mm]
A: 단면적 [mm^2]
sigma: 축응력 [MPa]
"""

import math


def read_axial_force() -> float:
    """축력을 kN 단위로 입력받는다."""
    while True:
        try:
            return float(
                input("축력 P [kN] (양수: 인장, 음수: 압축): ").strip()
            )
        except ValueError:
            print("축력은 숫자로 입력하세요. 예: -100 또는 50")


def read_positive_diameter() -> float:
    """0보다 큰 직경을 mm 단위로 입력받는다."""
    while True:
        try:
            diameter_mm = float(
                input("원형 봉의 직경 d [mm]: ").strip()
            )

            if diameter_mm <= 0:
                print("직경은 0보다 큰 값이어야 합니다.")
                continue

            return diameter_mm

        except ValueError:
            print("직경은 숫자로 입력하세요. 예: 20 또는 12.5")


def calculate_area(diameter_mm: float) -> float:
    """원형 봉의 단면적을 mm^2 단위로 계산한다."""
    return math.pi * diameter_mm**2 / 4


def calculate_stress(force_kn: float, area_mm2: float) -> float:
    """축응력을 MPa 단위로 계산한다."""
    force_n = force_kn * 1000
    return force_n / area_mm2


def main() -> None:
    print("=" * 48)
    print("          원형 봉 축응력 계산기")
    print("=" * 48)
    print("축력 단위: kN | 직경 단위: mm | 응력 단위: MPa")
    print()

    force_kn = read_axial_force()
    diameter_mm = read_positive_diameter()

    area_mm2 = calculate_area(diameter_mm)
    stress_mpa = calculate_stress(force_kn, area_mm2)

    if force_kn > 0:
        load_type = "인장"
    elif force_kn < 0:
        load_type = "압축"
    else:
        load_type = "무하중"

    print("\n[계산 결과]")
    print(f"단면적 A = πd²/4 = {area_mm2:.3f} mm²")
    print(f"축응력 σ = P/A = {stress_mpa:.2f} MPa ({load_type})")


if __name__ == "__main__":
    main()