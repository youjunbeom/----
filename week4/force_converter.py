"""힘 단위 변환 프로그램"""

TO_NEWTON = {
    "n": 1,
    "kn": 1000,
    "mn": 0.001,
    "un": 0.000001,
    "μn": 0.000001,
    "kgf": 9.80665,
    "gf": 0.00980665,
    "lbf": 4.4482216152605,
    "kip": 4448.2216152605,
    "dyn": 0.00001,
}

UNIT_NAMES = {
    "n": "N",
    "kn": "kN",
    "mn": "mN",
    "un": "μN",
    "μn": "μN",
    "kgf": "kgf",
    "gf": "gf",
    "lbf": "lbf",
    "kip": "kip",
    "dyn": "dyn",
}


def normalize_unit(unit):
    return unit.strip().lower().replace(" ", "")


def convert_force(value, from_unit, to_unit):
    from_unit = normalize_unit(from_unit)
    to_unit = normalize_unit(to_unit)

    if from_unit not in TO_NEWTON:
        raise ValueError("지원하지 않는 입력 단위입니다.")

    if to_unit not in TO_NEWTON:
        raise ValueError("지원하지 않는 출력 단위입니다.")

    # 입력값을 뉴턴으로 변환
    value_in_newton = value * TO_NEWTON[from_unit]

    # 뉴턴을 목표 단위로 변환
    return value_in_newton / TO_NEWTON[to_unit]


def main():
    print("=== 힘 단위 변환기 ===")
    print("지원 단위: N, kN, mN, μN, kgf, gf, lbf, kip, dyn")
    print("종료하려면 q를 입력하세요.")

    while True:
        value_input = input("\n변환할 값을 입력하세요: ")

        if value_input.lower() == "q":
            print("프로그램을 종료합니다.")
            break

        try:
            value = float(value_input)
            from_unit = input("현재 단위: ")
            to_unit = input("변환할 단위: ")

            result = convert_force(value, from_unit, to_unit)
            unit_name = UNIT_NAMES[normalize_unit(to_unit)]

            print(f"\n결과: {value:g} {from_unit} = {result:.12g} {unit_name}")

        except ValueError as error:
            print(f"입력 오류: {error}")


if __name__ == "__main__":
    main()

    