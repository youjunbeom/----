import tkinter as tk
from tkinter import ttk, messagebox


UNIT_TO_NEWTON = {
    "N": 1.0,
    "kN": 1000.0,
    "mN": 0.001,
    "μN": 0.000001,
    "kgf": 9.80665,
    "gf": 0.00980665,
    "lbf": 4.4482216152605,
    "kip": 4448.2216152605,
    "dyn": 0.00001,
}


def convert_force(value, from_unit, to_unit):
    newton = value * UNIT_TO_NEWTON[from_unit]
    return newton / UNIT_TO_NEWTON[to_unit]


def calculate():
    try:
        value_text = value_entry.get().strip()

        if value_text == "":
            raise ValueError("숫자를 입력하세요.")

        value = float(value_text)
        from_unit = from_unit_box.get()
        to_unit = to_unit_box.get()

        result = convert_force(value, from_unit, to_unit)

        result_label.config(
            text=f"{value:g} {from_unit} = {result:.12g} {to_unit}",
            foreground="blue",
        )

    except ValueError as error:
        result_label.config(
            text=f"입력 오류: {error}",
            foreground="red",
        )


def clear():
    value_entry.delete(0, tk.END)
    from_unit_box.set("N")
    to_unit_box.set("N")
    result_label.config(text="", foreground="black")
    value_entry.focus()


# 별도의 GUI 창 생성
window = tk.Tk()
window.title("힘 단위 계산기")
window.geometry("450x330")
window.resizable(False, False)

# 제목
title_label = tk.Label(
    window,
    text="힘 단위 계산기",
    font=("Arial", 20, "bold"),
)
title_label.pack(pady=20)

# 숫자 입력 영역
value_frame = ttk.Frame(window)
value_frame.pack(fill="x", padx=40, pady=5)

ttk.Label(
    value_frame,
    text="입력 값:",
    width=12,
).pack(side="left")

value_entry = ttk.Entry(value_frame)
value_entry.pack(side="left", fill="x", expand=True)

# 현재 단위 영역
from_frame = ttk.Frame(window)
from_frame.pack(fill="x", padx=40, pady=5)

ttk.Label(
    from_frame,
    text="현재 단위:",
    width=12,
).pack(side="left")

from_unit_box = ttk.Combobox(
    from_frame,
    values=list(UNIT_TO_NEWTON.keys()),
    state="readonly",
)
from_unit_box.pack(side="left", fill="x", expand=True)
from_unit_box.set("N")

# 변환 단위 영역
to_frame = ttk.Frame(window)
to_frame.pack(fill="x", padx=40, pady=5)

ttk.Label(
    to_frame,
    text="변환 단위:",
    width=12,
).pack(side="left")

to_unit_box = ttk.Combobox(
    to_frame,
    values=list(UNIT_TO_NEWTON.keys()),
    state="readonly",
)
to_unit_box.pack(side="left", fill="x", expand=True)
to_unit_box.set("N")

# 버튼 영역
button_frame = ttk.Frame(window)
button_frame.pack(pady=20)

ttk.Button(
    button_frame,
    text="계산",
    width=15,
    command=calculate,
).pack(side="left", padx=5)

ttk.Button(
    button_frame,
    text="초기화",
    width=15,
    command=clear,
).pack(side="left", padx=5)

# 결과 표시
result_label = tk.Label(
    window,
    text="",
    font=("Arial", 13, "bold"),
)
result_label.pack(pady=10)

# Enter 키로 계산
window.bind("<Return>", lambda event: calculate())

# 처음 실행할 때 입력창에 커서 표시
value_entry.focus()

# Enter 키를 누르면 계산 함수 실행
def enter_key_calculate(event):
    calculate()


window.bind("<Return>", enter_key_calculate)
# Esc 키를 누르면 계산기 초기 상태로 되돌리기
def escape_key_clear(event):
    clear()


window.bind("<Escape>", escape_key_clear)
# Delete 키를 누르면 계산기 종료
def delete_key_exit(event):
    window.destroy()


window.bind("<Delete>", delete_key_exit)

# 별도 GUI 창 계속 실행
window.mainloop()