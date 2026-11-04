import csv
import getpass
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, quote_plus

try:
    import requests
except ModuleNotFoundError as error:
    if error.name != "requests":
        raise
    raise SystemExit(
        "필요한 패키지 requests가 없습니다. "
        "터미널에서 'python -m pip install -r requirements.txt'를 실행하세요."
    ) from error


API_URL = "https://apihub.kma.go.kr/api/typ01/url/kma_sfctm3.php"
TIMEOUT_SECONDS = 30
OUTPUT_DIRECTORY = Path(__file__).resolve().parent
CSV_PATH = OUTPUT_DIRECTORY / "practice_weather.csv"
RAW_PATH = OUTPUT_DIRECTORY / "practice_weather_raw.txt"

FIELD_NUMBERS = {"TM": 1, "WS": 4, "TA": 12, "HM": 14}
COLUMNS = ["datetime", "temperature_C", "humidity_pct", "wind_speed_ms"]
MISSING_VALUES = {"", "-", "--", "NA", "N/A", "NULL", "-99", "-99.0", "-999", "-999.0", "-9999", "-9999.0"}
FIELD_DEFINITION_PATTERN = re.compile(
    r"^\s*#\s*(\d+)\s*\.\s*(TM|WS|TA|HM)\s*:",
    re.IGNORECASE,
)


def _error_message(body: str) -> str:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body.strip() or "응답 본문에서 오류 메시지를 찾을 수 없습니다."

    if isinstance(payload, dict):
        candidates = [payload]
        result = payload.get("result")
        if isinstance(result, dict):
            candidates.append(result)
        for candidate in candidates:
            message = candidate.get("message")
            if isinstance(message, str):
                return message
    return body.strip() or "응답 본문에서 오류 메시지를 찾을 수 없습니다."


def _api_error_message(body: str) -> str | None:
    """HTTP 200 응답 안에 포함된 API 자체의 실패 상태를 확인한다."""
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None
    result = payload.get("result")
    if not isinstance(result, dict):
        return None

    status = result.get("status")
    try:
        status_code = int(status)
    except (TypeError, ValueError):
        return None
    if status_code < 400:
        return None
    return _error_message(body)


def _redact_sensitive_text(text: str, api_key: str) -> str:
    text = re.sub(r"https?://\S+", "[요청 주소 생략]", text)
    for key_form in {api_key, quote(api_key, safe=""), quote_plus(api_key)}:
        if key_form:
            text = text.replace(key_form, "[인증키 생략]")
    return text


def _find_field_numbers(lines: list[str]) -> dict[str, int]:
    """공식 '# 번호. 필드명 :' 형식의 정의줄만 읽어 1-based 위치를 반환한다."""
    found: dict[str, int] = {}
    for line in lines:
        match = FIELD_DEFINITION_PATTERN.match(line)
        if match is None:
            continue
        number, name = match.groups()
        name = name.upper()
        position = int(number)
        if name in found and found[name] != position:
            raise ValueError(f"헤더에서 {name}의 필드 번호가 일치하지 않습니다.")
        found[name] = position

    missing = set(FIELD_NUMBERS) - found.keys()
    if missing:
        raise ValueError(f"응답 헤더에서 필드 번호를 확인할 수 없습니다: {', '.join(sorted(missing))}")
    for name, expected_position in FIELD_NUMBERS.items():
        if found[name] != expected_position:
            raise ValueError(
                f"응답 헤더의 {name} 번호가 예상값 {expected_position}과 다릅니다."
            )
    return found


def _measurement(token: str, field_name: str) -> float | str:
    """공식 응답의 결측 표기를 빈 값으로 바꾸고, 음수 수치는 그대로 보존한다."""
    normalized = token.strip().upper()
    if normalized in MISSING_VALUES or (
        field_name in {"WS", "HM"} and normalized in {"-9", "-9.0"}
    ):
        return ""
    try:
        return float(token)
    except ValueError as error:
        raise ValueError("기온·습도·풍속 필드에 숫자가 아닌 값이 있습니다.") from error


def _parse_response(body: str) -> tuple[list[dict[str, object]], dict[str, int]]:
    """설명줄의 필드 번호를 검증하고 공백 구분 자료행을 표 형태로 변환한다."""
    lines = body.splitlines()
    field_numbers = _find_field_numbers(lines)
    rows: list[dict[str, object]] = []

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        if len(fields) < max(field_numbers.values()):
            raise ValueError(f"{line_number}번째 응답 행의 필드 수가 헤더 번호보다 적습니다.")
        try:
            timestamp = datetime.strptime(fields[field_numbers["TM"] - 1], "%Y%m%d%H%M")
        except ValueError as error:
            raise ValueError(f"{line_number}번째 응답 행의 TM 시간이 올바르지 않습니다.") from error

        rows.append(
            {
                "datetime": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "temperature_C": _measurement(fields[field_numbers["TA"] - 1], "TA"),
                "humidity_pct": _measurement(fields[field_numbers["HM"] - 1], "HM"),
                "wind_speed_ms": _measurement(fields[field_numbers["WS"] - 1], "WS"),
            }
        )

    if not rows:
        raise ValueError("응답에서 기상 자료행을 찾을 수 없습니다.")
    return rows, field_numbers


def _sort_and_remove_duplicates(
    rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], int]:
    """시간순 정렬 후 완전히 같은 시각·값의 중복행만 제거한다."""
    rows_by_time: dict[str, dict[str, object]] = {}
    duplicates = 0
    for row in rows:
        timestamp = str(row["datetime"])
        previous = rows_by_time.get(timestamp)
        if previous is None:
            rows_by_time[timestamp] = row
        elif previous == row:
            duplicates += 1
        else:
            raise ValueError(f"{timestamp} 시각에 서로 다른 자료가 중복되어 저장을 중단합니다.")
    return [rows_by_time[key] for key in sorted(rows_by_time)], duplicates


def _save_csv(rows: list[dict[str, object]]) -> None:
    """지정한 열 순서와 UTF-8 BOM 인코딩으로 CSV를 저장한다."""
    with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _print_summary(rows: list[dict[str, object]], duplicate_count: int) -> None:
    """저장된 표의 크기, 결측치, 시간 범위와 중복 처리 결과를 출력한다."""
    print(f"행 수: {len(rows)}")
    print(f"중복 제거 행 수: {duplicate_count}")
    print("열별 결측 수:")
    for column in COLUMNS:
        missing_count = sum(row[column] == "" for row in rows)
        print(f"  {column}: {missing_count}")
    print(f"첫 시각: {rows[0]['datetime']}")
    print(f"마지막 시각: {rows[-1]['datetime']}")
    print(f"저장 위치: {CSV_PATH}")
    print(f"원본 응답 저장 위치: {RAW_PATH}")


def main() -> None:
    """인증키를 안전하게 입력받아 응답 원문과 정리된 CSV를 저장한다."""
    api_key = getpass.getpass("기상청 API 인증키: ")
    if not api_key:
        print("인증키가 입력되지 않아 요청을 중단합니다.")
        return

    params = {
        "tm1": "201510080000",
        "tm2": "201510142300",
        "stn": "108",
        "help": "1",
        "authKey": api_key,
    }

    try:
        response = requests.get(API_URL, params=params, timeout=TIMEOUT_SECONDS)
    except requests.RequestException:
        print("요청 중 네트워크 오류가 발생했습니다. 인증키와 요청 주소는 출력하지 않습니다.")
        return

    RAW_PATH.write_bytes(response.content)
    content_type = response.headers.get("Content-Type", "").lower()
    if not response.encoding or (
        response.encoding.lower() == "iso-8859-1" and "charset=" not in content_type
    ):
        response.encoding = response.apparent_encoding or "utf-8"
    body = response.text

    print(f"HTTP 상태 코드: {response.status_code}")
    if not response.ok:
        message = _redact_sensitive_text(_error_message(body), api_key)
        print(f"API 요청 실패: {message}")
        print(f"원본 응답 저장 위치: {RAW_PATH}")
        return
    api_error = _api_error_message(body)
    if api_error:
        message = _redact_sensitive_text(api_error, api_key)
        print(f"API 요청 실패: {message}")
        print(f"원본 응답 저장 위치: {RAW_PATH}")
        return

    try:
        rows, field_numbers = _parse_response(body)
        rows, duplicate_count = _sort_and_remove_duplicates(rows)
        _save_csv(rows)
    except ValueError as error:
        print(f"응답 자료 처리 실패: {_redact_sensitive_text(str(error), api_key)}")
        print(f"원본 응답 저장 위치: {RAW_PATH}")
        return

    print("헤더에서 확인한 필드 번호:")
    for name in ("TM", "WS", "TA", "HM"):
        print(f"  {name}: {field_numbers[name]}")
    _print_summary(rows, duplicate_count)


if __name__ == "__main__":
    main()
