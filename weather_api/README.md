# Weather data collection and plotting

This folder contains a script to collect hourly weather observations from the
Korea Meteorological Administration (KMA) API and a script to plot and compare
the collected temperatures.

## Requirements

Use Python 3.10 or later. Install the packages from this folder:

```powershell
python -m pip install -r requirements.txt
```

## 1. Collect weather observations

Run:

```powershell
python collect_weather.py
```

The script prompts for the KMA API key using `getpass`, so the key is not
displayed while entering it. The current request settings in
`collect_weather.py` are:

- Period: `2015-10-08 00:00` through `2015-10-14 23:00` (KST)
- Station: `108`
- Help fields: enabled
- Request timeout: 30 seconds

The script reads the field numbers from the response header, parses the
whitespace-separated observations, sorts them by time, and checks for
duplicates. It saves:

- `practice_weather.csv` — processed data, in UTF-8 with BOM
- `practice_weather_raw.txt` — original API response for troubleshooting

The CSV columns are `datetime`, `temperature_C`, `humidity_pct`, and
`wind_speed_ms`. Missing measurements are written as empty cells. If identical
timestamps have conflicting measurements, processing stops rather than
choosing a value silently.

To collect another period, change `tm1` and `tm2` in the `params` dictionary in
`collect_weather.py`, then run the collection script again.

## 2. Plot and compare temperatures

After collection completes successfully, run:

```powershell
python "practice practice weather.py"
```

The graph script reads `practice_weather.csv`; it does not call the API. It
sorts the observations by time, inserts missing hours between the first and
last records, and leaves gaps in the plotted line where a time or temperature
is missing. It saves `practice_weather.png` and displays the plot.

The script also compares the mean of non-missing temperatures in
`practice_weather.csv` with the original period in `weather.csv`, then prints
the difference in one sentence. Keep `weather.csv` in this folder if you want
to retain this baseline comparison.

## Output files

| File | Purpose |
| --- | --- |
| `weather.csv` | Baseline observations for 2025-10-01 through 2025-10-07 |
| `practice_weather.csv` | Observations collected by `collect_weather.py` |
| `practice_weather_raw.txt` | Original response for the practice-period request |
| `temperature.png` | Baseline temperature plot |
| `practice_weather.png` | Practice-period temperature plot |
