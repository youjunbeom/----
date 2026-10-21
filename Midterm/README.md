# Exam Study Schedule

Complete source code from `study_schedule.py`:

```python
import calendar
import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import ttk

# Korean labels are escaped so the source remains safe across Windows encodings.
TITLE = "\uc2dc\ud5d8 \uacf5\ubd80 \uc2dc\uac04\ud45c"
WEEKDAYS = "\uc6d4\ud654\uc218\ubaa9\uae08\ud1a0\uc77c"


def make_schedule(exams, hours_per_day, start_time, exam_times):
    """Assign sessions by exam urgency and leave exam-duration slots free."""
    today = date.today()
    schedule = {}
    current = today
    while current <= max(day for _, day in exams):
        # A subject is not scheduled on its own exam day. Other subjects with
        # later exam dates remain eligible for study that day.
        upcoming = [(name, day) for name, day in exams if day > current]
        if upcoming:
            # Allocate each one-hour slot by urgency. A closer exam has a larger
            # weight, while the divisor spreads time across the day's assignments.
            counts = {name: 0 for name, _ in upcoming}
            sessions = []
            for _ in range(hours_per_day):
                name, _ = max(
                    upcoming,
                    key=lambda item: (1 / ((item[1] - current).days + 1)) / (counts[item[0]] + 1),
                )
                counts[name] += 1
                sessions.append(name)
            # Record actual session times. Leave every one-hour study block
            # that overlaps an exam's full duration empty, then move it forward.
            slot = datetime.combine(current, start_time)
            timed_sessions = []
            while len(timed_sessions) < len(sessions):
                slot_end = slot + timedelta(hours=1)
                exam_ranges = [
                    (
                        datetime.combine(current, exam_time),
                        datetime.combine(current, exam_time) + timedelta(hours=duration),
                    )
                    for _, exam_time, duration in exam_times.get(current, [])
                ]
                if any(slot < exam_end and slot_end > exam_start for exam_start, exam_end in exam_ranges):
                    slot = slot_end
                    continue
                timed_sessions.append((sessions[len(timed_sessions)], slot.time()))
                slot = slot_end
            schedule[current] = timed_sessions
        current += timedelta(days=1)
    return schedule


class DatePicker(tk.Toplevel):
    """Popup calendar that returns a selected date to the subject row."""
    def __init__(self, parent, initial, callback):
        super().__init__(parent)
        self.title("\ub0a0\uc9dc \uc120\ud0dd")
        self.resizable(False, False)
        self.callback = callback
        self.year, self.month = initial.year, initial.month
        self.body = ttk.Frame(self, padding=10)
        self.body.pack()
        self.draw()
        self.transient(parent)
        self.grab_set()

    def draw(self):
        for widget in self.body.winfo_children():
            widget.destroy()
        nav = ttk.Frame(self.body)
        nav.grid(row=0, column=0, columnspan=7, pady=(0, 6))
        ttk.Button(nav, text="\u25c0", command=lambda: self.shift(-1)).pack(side="left")
        ttk.Label(nav, text=f"{self.year}\ub144 {self.month}\uc6d4", width=16, anchor="center").pack(side="left")
        ttk.Button(nav, text="\u25b6", command=lambda: self.shift(1)).pack(side="left")
        for col, name in enumerate(WEEKDAYS):
            ttk.Label(self.body, text=name, width=4, anchor="center").grid(row=1, column=col)
        weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(self.year, self.month)
        for row, week in enumerate(weeks, 2):
            for col, number in enumerate(week):
                if number:
                    ttk.Button(self.body, text=str(number), width=4,
                               command=lambda day=number: self.select(day)).grid(row=row, column=col, padx=1, pady=1)

    def shift(self, amount):
        month = self.month + amount
        if month < 1:
            self.year, self.month = self.year - 1, 12
        elif month > 12:
            self.year, self.month = self.year + 1, 1
        else:
            self.month = month
        self.draw()

    def select(self, day):
        self.callback(date(self.year, self.month, day))
        self.destroy()


class StudyScheduleApp:
    def __init__(self, root):
        self.root = root
        root.title(TITLE)
        root.geometry("1050x760")
        self.rows = []
        self.schedule = {}
        self.load_scores = {}
        self.exams_by_day = {}
        self.year, self.month = date.today().year, date.today().month
        main = ttk.Frame(root, padding=14)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text=TITLE, font=("Malgun Gothic", 16, "bold")).pack(anchor="w")
        ttk.Label(main, text="\uacfc\ubaa9\uc758 \uc2dc\ud5d8 \ub0a0\uc9dc\ub97c \ub2ec\ub825\uc5d0\uc11c \uace0\ub974\uace0, \uc6d4\uac04 \uacf5\ubd80 \uc2dc\uac04\ud45c\ub97c \ud655\uc778\ud558\uc138\uc694.").pack(anchor="w", pady=(4, 10))
        self.subject_box = ttk.LabelFrame(main, text="\uacfc\ubaa9 \ubc0f \uc2dc\ud5d8 \ub0a0\uc9dc", padding=8)
        self.subject_box.pack(fill="x")
        head = ttk.Frame(self.subject_box)
        head.pack(fill="x")
        ttk.Label(head, text="\uacfc\ubaa9\uba85", width=28).pack(side="left")
        ttk.Label(head, text="\uc2dc\ud5d8 \ub0a0\uc9dc / \uc2dc\uac04 / \uc2dc\ud5d8 \uae30\uac04 (\uc2dc\uac04)").pack(side="left")
        self.row_box = ttk.Frame(self.subject_box)
        self.row_box.pack(fill="x")
        ttk.Button(self.subject_box, text="\uacfc\ubaa9 \ucd94\uac00", command=self.add_row).pack(anchor="w", pady=5)
        settings = ttk.Frame(main)
        settings.pack(fill="x", pady=8)
        ttk.Label(settings, text="\ud558\ub8e8 \uacf5\ubd80 \uc2dc\uac04 (\uc2dc\uac04)").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=3)
        self.hours = ttk.Entry(settings, width=8)
        self.hours.insert(0, "3")
        self.hours.grid(row=0, column=1, sticky="w")
        ttk.Label(settings, text="\uacf5\ubd80 \uc2dc\uc791 \uc2dc\uac04").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=3)
        time_choices = ttk.Frame(settings)
        time_choices.grid(row=1, column=1, sticky="w")
        self.start_hour = ttk.Combobox(time_choices, width=4, state="readonly", values=[f"{hour:02d}" for hour in range(24)])
        self.start_hour.set("00")
        self.start_hour.pack(side="left")
        ttk.Label(time_choices, text="\uc2dc").pack(side="left", padx=(2, 6))
        self.start_minute = ttk.Spinbox(time_choices, width=4, from_=0, to=59, increment=1, wrap=True, format="%02.0f")
        self.start_minute.set("00")
        self.start_minute.pack(side="left")
        ttk.Label(time_choices, text="\ubd84").pack(side="left", padx=(2, 0))
        ttk.Button(main, text="\ub2ec\ub825 \uc2dc\uac04\ud45c \ub9cc\ub4e4\uae30", command=self.generate).pack(anchor="w", pady=(0, 6))
        self.message = ttk.Label(main, text="")
        self.message.pack(anchor="w", pady=4)
        self.cal_box = ttk.LabelFrame(main, text="\uc6d4\uac04 \uacf5\ubd80 \ub2ec\ub825", padding=8)
        self.cal_box.pack(fill="both", expand=True)
        nav = ttk.Frame(self.cal_box)
        nav.pack(fill="x", pady=(0, 5))
        ttk.Button(nav, text="\u25c0", command=lambda: self.shift_month(-1)).pack(side="left")
        self.month_label = ttk.Label(nav, text="", anchor="center", font=("Malgun Gothic", 12, "bold"))
        self.month_label.pack(side="left", expand=True)
        ttk.Button(nav, text="\u25b6", command=lambda: self.shift_month(1)).pack(side="right")
        legend = ttk.Frame(self.cal_box)
        legend.pack(fill="x", pady=(0, 5))
        for label, color in [
            ("\ub9ce\uc74c", "#f4a3a3"),
            ("\ub192\uc74c", "#ffe28a"),
            ("\ubcf4\ud1b5", "#9ad7a1"),
            ("\uc801\uc74c", "#9cc9f0"),
        ]:
            tk.Label(legend, text=f"  {label}  ", bg=color, relief="solid", borderwidth=1).pack(side="left", padx=3)
        self.grid = ttk.Frame(self.cal_box)
        self.grid.pack(fill="both", expand=True)
        self.add_row()
        self.draw_month()

    def add_row(self):
        row = ttk.Frame(self.row_box)
        row.pack(fill="x", pady=2)
        name = ttk.Entry(row, width=28)
        name.pack(side="left", padx=(0, 8))
        selected = tk.StringVar()
        ttk.Entry(row, textvariable=selected, width=13, state="readonly").pack(side="left", padx=(0, 4))
        ttk.Button(row, text="\ub2ec\ub825\uc5d0\uc11c \uc120\ud0dd", command=lambda: self.pick(selected)).pack(side="left", padx=(0, 5))
        exam_hour = ttk.Combobox(row, width=3, state="readonly", values=[f"{hour:02d}" for hour in range(24)])
        exam_hour.set("09")
        exam_hour.pack(side="left")
        ttk.Label(row, text="\uc2dc").pack(side="left", padx=(2, 3))
        exam_minute = ttk.Spinbox(row, width=3, from_=0, to=59, increment=1, wrap=True, format="%02.0f")
        exam_minute.set("00")
        exam_minute.pack(side="left")
        ttk.Label(row, text="\ubd84").pack(side="left", padx=(2, 5))
        duration = ttk.Spinbox(row, width=3, from_=1, to=12, increment=1, wrap=False)
        duration.set("2")
        duration.pack(side="left")
        ttk.Label(row, text="\uc2dc\uac04").pack(side="left", padx=(2, 5))
        ttk.Button(row, text="\uc0ad\uc81c", command=lambda: self.remove(row)).pack(side="left")
        self.rows.append((row, name, selected, exam_hour, exam_minute, duration))

    def pick(self, selected):
        try:
            initial = date.fromisoformat(selected.get()) if selected.get() else date.today()
        except ValueError:
            initial = date.today()
        DatePicker(self.root, initial, lambda value: selected.set(value.isoformat()))

    def remove(self, row):
        self.rows = [item for item in self.rows if item[0] != row]
        row.destroy()

    def generate(self):
        exams = []
        exam_times = {}
        try:
            for index, (_, name_entry, selected, exam_hour, exam_minute, duration_entry) in enumerate(self.rows, 1):
                name = name_entry.get().strip()
                if not name:
                    raise ValueError(f"{index}\ubc88\uc9f8 \uacfc\ubaa9\uba85\uc744 \uc785\ub825\ud574 \uc8fc\uc138\uc694.")
                if not selected.get():
                    raise ValueError(f"{name}: \ub2ec\ub825\uc5d0\uc11c \uc2dc\ud5d8 \ub0a0\uc9dc\ub97c \uace0\ub974\uc138\uc694.")
                exam_day = date.fromisoformat(selected.get())
                if exam_day < date.today():
                    raise ValueError(f"{name}: \uc624\ub298 \uc774\ud6c4 \ub0a0\uc9dc\ub97c \uc120\ud0dd\ud574 \uc8fc\uc138\uc694.")
                exams.append((name, exam_day))
                exam_time = datetime.strptime(f"{exam_hour.get()}:{exam_minute.get()}", "%H:%M").time()
                duration = int(duration_entry.get())
                if not 1 <= duration <= 12:
                    raise ValueError(f"{name}: \uc2dc\ud5d8 \uae30\uac04\uc740 1~12\uc2dc\uac04\uc73c\ub85c \uc785\ub825\ud574 \uc8fc\uc138\uc694.")
                if datetime.combine(exam_day, exam_time) + timedelta(hours=duration) > datetime.combine(exam_day + timedelta(days=1), datetime.min.time()):
                    raise ValueError(f"{name}: \uc2dc\ud5d8 \uc885\ub8cc \uc2dc\uac01\uc774 \ub2e4\uc74c \ub0a0\uc744 \ub118\uc9c0 \uc54a\ub3c4\ub85d \uc124\uc815\ud574 \uc8fc\uc138\uc694.")
                exam_times.setdefault(exam_day, []).append((name, exam_time, duration))
            if not exams:
                raise ValueError("\uacfc\ubaa9\uc744 \ud558\ub098 \uc774\uc0c1 \ucd94\uac00\ud574 \uc8fc\uc138\uc694.")
            hours = int(self.hours.get())
            if not 1 <= hours <= 16:
                raise ValueError("\ud558\ub8e8 \uacf5\ubd80 \uc2dc\uac04\uc740 1~16\uc73c\ub85c \uc124\uc815\ud574 \uc8fc\uc138\uc694.")
            start_time = datetime.strptime(f"{self.start_hour.get()}:{self.start_minute.get()}", "%H:%M").time()
            conflicts = [
                (name, exam_time, duration)
                for entries in exam_times.values()
                for name, exam_time, duration in entries
                if exam_time == start_time
            ]
            if conflicts:
                self.choose_new_start_time(conflicts)
                return
        except ValueError as error:
            self.message.configure(text=str(error), foreground="#b00020")
            return
        self.schedule = make_schedule(exams, hours, start_time, exam_times)
        exam_by_subject = {name: exam_day for name, exam_day in exams}
        self.load_scores = {
            study_day: sum(
                1 / ((exam_by_subject[name] - study_day).days + 1)
                for name, _ in sessions
            )
            for study_day, sessions in self.schedule.items()
        }
        self.exams_by_day = exam_times
        first = min(day for _, day in exams)
        self.year, self.month = first.year, first.month
        self.start_time = start_time
        self.draw_month()
        self.message.configure(text="\uc2dc\uac04\ud45c\ub97c \ub9cc\ub4e4\uc5c8\uc2b5\ub2c8\ub2e4.", foreground="#176b36")

    def choose_new_start_time(self, conflicts):
        """Ask for another study start time when it matches an exam time."""
        dialog = tk.Toplevel(self.root)
        dialog.title("\uc2dc\uac04 \ub2e4\uc2dc \uc120\ud0dd")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text="\uacf5\ubd80 \uc2dc\uc791 \uc2dc\uac04\uacfc \uc2dc\ud5d8 \uc2dc\uc791 \uc2dc\uac04\uc774 \uac19\uc2b5\ub2c8\ub2e4.\n\ub2e4\ub978 \uc2dc\uac04\uc744 \uc120\ud0dd\ud574 \uc8fc\uc138\uc694.",
            justify="left",
        ).pack(anchor="w", pady=(0, 8))
        for name, exam_time, duration in conflicts:
            ttk.Label(frame, text=f"{name}: {exam_time:%H:%M} (\uc2dc\ud5d8 {duration}\uc2dc\uac04)", foreground="#b00020").pack(anchor="w")
        controls = ttk.Frame(frame)
        controls.pack(anchor="w", pady=10)
        hour = ttk.Combobox(controls, width=4, state="readonly", values=[f"{value:02d}" for value in range(24)])
        hour.set(self.start_hour.get())
        hour.pack(side="left")
        ttk.Label(controls, text="\uc2dc").pack(side="left", padx=(2, 6))
        minute = ttk.Spinbox(controls, width=4, from_=0, to=59, increment=1, wrap=True, format="%02.0f")
        minute.set(self.start_minute.get())
        minute.pack(side="left")
        ttk.Label(controls, text="\ubd84").pack(side="left", padx=(2, 0))

        def apply_time():
            self.start_hour.set(hour.get())
            self.start_minute.set(minute.get())
            dialog.destroy()
            self.generate()

        ttk.Button(frame, text="\uc801\uc6a9\ud558\uace0 \uc2dc\uac04\ud45c \ub9cc\ub4e4\uae30", command=apply_time).pack(anchor="e")

    def shift_month(self, amount):
        month = self.month + amount
        if month < 1:
            self.year, self.month = self.year - 1, 12
        elif month > 12:
            self.year, self.month = self.year + 1, 1
        else:
            self.month = month
        self.draw_month()

    def draw_month(self):
        for child in self.grid.winfo_children():
            child.destroy()
        self.month_label.configure(text=f"{self.year}\ub144 {self.month}\uc6d4")
        for col, weekday in enumerate(WEEKDAYS):
            ttk.Label(self.grid, text=weekday, anchor="center").grid(row=0, column=col, sticky="ew")
            self.grid.columnconfigure(col, weight=1, uniform="day")
        weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(self.year, self.month)
        sorted_loads = sorted(self.load_scores.values())
        load_colors = ["#9cc9f0", "#9ad7a1", "#ffe28a", "#f4a3a3"]
        for row_index, week in enumerate(weeks, 1):
            self.grid.rowconfigure(row_index, weight=1, uniform="week")
            for col, number in enumerate(week):
                cell = ttk.Frame(self.grid, relief="solid", borderwidth=1, padding=3)
                cell.grid(row=row_index, column=col, sticky="nsew", padx=1, pady=1)
                if not number:
                    continue
                day = date(self.year, self.month, number)
                if day in self.load_scores and sorted_loads:
                    score = self.load_scores[day]
                    lower = sum(value < score for value in sorted_loads)
                    equal = sum(value == score for value in sorted_loads)
                    percentile = (lower + equal / 2) / len(sorted_loads)
                    color_index = min(3, int(percentile * 4))
                    tk.Button(
                        cell,
                        text=str(number),
                        bg=load_colors[color_index],
                        activebackground=load_colors[color_index],
                        relief="flat",
                        command=lambda selected_day=day: self.show_day_plan(selected_day),
                    ).pack(anchor="nw")
                else:
                    ttk.Button(
                        cell,
                        text=str(number),
                        command=lambda selected_day=day: self.show_day_plan(selected_day),
                    ).pack(anchor="nw")
                for name, exam_time, duration in self.exams_by_day.get(day, []):
                    exam_end = (datetime.combine(day, exam_time) + timedelta(hours=duration)).time()
                    ttk.Label(cell, text=f"\uc2dc\ud5d8 {exam_time:%H:%M}-{exam_end:%H:%M} {name}", foreground="#b00020", wraplength=120).pack(anchor="nw")
                for name, session_time in self.schedule.get(day, []):
                    slot = datetime.combine(day, session_time)
                    end = slot + timedelta(minutes=50)
                    ttk.Label(cell, text=f"{slot:%H:%M}-{end:%H:%M} {name}", wraplength=100).pack(anchor="nw")

    def show_day_plan(self, day):
        """Show the selected calendar day's complete exam and study plan."""
        detail = tk.Toplevel(self.root)
        detail.title(f"{day:%Y-%m-%d} \ub2f9\uc77c \uacf5\ubd80 \uacc4\ud68d")
        detail.geometry("380x420")
        detail.transient(self.root)
        content = ttk.Frame(detail, padding=12)
        content.pack(fill="both", expand=True)
        ttk.Button(content, text="\ub2eb\uae30", command=detail.destroy).pack(side="bottom", anchor="e", pady=(8, 0))
        weekday = WEEKDAYS[day.weekday()]
        plan_text = tk.Text(content, wrap="word", font=("Malgun Gothic", 10), height=18)
        scrollbar = ttk.Scrollbar(content, orient="vertical", command=plan_text.yview)
        plan_text.configure(yscrollcommand=scrollbar.set)
        plan_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        plan_text.insert("end", f"{day:%Y\ub144 %m\uc6d4 %d\uc77c} ({weekday})\n\n", "heading")
        plan_text.tag_configure("heading", font=("Malgun Gothic", 14, "bold"))
        exam_entries = self.exams_by_day.get(day, [])
        if exam_entries:
            plan_text.insert("end", "\uc2dc\ud5d8\n", "section")
            plan_text.tag_configure("section", font=("Malgun Gothic", 11, "bold"))
            for name, exam_time, duration in exam_entries:
                exam_start = datetime.combine(day, exam_time)
                exam_end = exam_start + timedelta(hours=duration)
                plan_text.insert("end", f"  {exam_start:%H:%M}-{exam_end:%H:%M}  {name} (\ucd1d {duration}\uc2dc\uac04)\n", "exam")
            plan_text.tag_configure("exam", foreground="#b00020")
            plan_text.insert("end", "\n")
        plan_text.insert("end", "\uacf5\ubd80 \uacc4\ud68d\n", "section")
        sessions = self.schedule.get(day, [])
        if not sessions:
            plan_text.insert("end", "  \uc774 \ub0a0\uc5d0 \ubc30\uc815\ub41c \uacf5\ubd80 \uacc4\ud68d\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.\n")
        else:
            for index, (name, session_time) in enumerate(sessions, start=1):
                slot = datetime.combine(day, session_time)
                end = slot + timedelta(minutes=50)
                plan_text.insert("end", f"{index}. {slot:%H:%M}-{end:%H:%M}  {name} \uacf5\ubd80\n")
                if index < len(sessions):
                    plan_text.insert("end", f"   {end:%H:%M}-{slot + timedelta(hours=1):%H:%M}  \ud734\uc2dd\n", "break")
            plan_text.tag_configure("break", foreground="#666666")
        plan_text.configure(state="disabled")


def main():
    root = tk.Tk()
    StudyScheduleApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
```
