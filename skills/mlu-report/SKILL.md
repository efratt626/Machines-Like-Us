---
name: mlu-report
description: >
  Generates a styled Excel QBR or Monthly report for the Machines Like Us podcast
  from platform CSV exports (Apple, Spotify, YouTube). Use this skill whenever the
  user says anything like "generate the Q2 QBR", "create the March monthly report",
  "run the MLU report", "build the report for Q3", or uploads the platform CSV files
  and asks to produce the report. Also trigger when the user says "run the report"
  or "make the report" in the context of Machines Like Us data.
---

# MLU Report Skill

This skill produces a 4-tab Excel workbook from platform analytics exports:
- **Followers** – 3-line chart (Apple Net Followers, Spotify Followers, YouTube Subscribers) + data table
- **Apple** – dark red area chart of daily Unique Listeners + raw data table
- **Spotify** – dark red area chart of daily Plays + raw data table
- **YouTube** – dark red area chart of daily Monthly Audience + raw data table

## Step 1 – Identify inputs

Ask the user (or infer from context):
1. **Root folder** – the folder containing `Apple/`, `Spotify/`, `YouTube/` subfolders. For QBRs this is typically `Machines Like Us/QBRs/<Quarter>/`. For monthly reports it will be a monthly folder.
2. **Period label** – e.g. `Q1 2026`, `Q2 2026`, `March 2026`. Infer from folder names or filenames if obvious; otherwise ask.
3. **Report type** – `QBR` (quarterly) or `Monthly`. Infer from context; ask if unclear.

## Step 2 – Validate folder structure

Before running, confirm these paths exist under the root folder. Report any that are missing clearly before proceeding.

```
<root>/
  Apple/
    Apple Monthly Listeners/     ← one CSV per month
                                   columns: Show ID, Date (YYYYMMDD), Total Time Listened,
                                            Plays, Unique Listeners, Unique Engaged Listeners
    Apple Monthly Subscribers/   ← one CSV per month
                                   columns: Date (YYYYMMDD), Net Followers,
                                            Gross Followers, Gross Unfollowers
  Spotify/
    *Spotify_Listeners*.csv      ← single file
                                   columns: Date, Plays, Consumption hours, Followers
  YouTube/
    *AllViewers*.csv             ← single file
                                   columns: Date, Monthly audience
    *Subscribers*.csv            ← single file
                                   columns: Date, Subscribers
```

## Step 3 – Run the build script

The bundled script at `scripts/build_report.py` (relative to this skill file) handles all
data loading, chart generation, and Excel assembly. Call it with:

```bash
python3 "<skill_dir>/scripts/build_report.py" "<root_folder>" "<period>" "<report_type>"
```

Where:
- `<skill_dir>` is the directory containing this SKILL.md file:
  `/Users/emmafrattasio/Desktop/Claude/Machines Like Us/skills/mlu-report`
- `<root_folder>` is the absolute path the user specified
- `<period>` is the period label (e.g. `Q1 2026` or `March 2026`)
- `<report_type>` is `QBR` or `Monthly`

The script prints `SAVED:<path>` on success or `ERROR:<message>` and exits with code 1 on failure.

## Step 4 – Report to the user

On success, tell the user the full path to the saved file. On failure, surface the error
message clearly so they know exactly which file or folder is missing.

## Chart style reference (already encoded in the script — for reference only)

| Element | Value |
|---|---|
| Background | `#F2EDE3` (cream) |
| Area chart fill | `#7B1E1E` (dark red, no outline) |
| Apple line | `#5B2C8D` |
| Spotify line | `#1A4B8C` |
| YouTube line | `#C0392B` |
| Grid | Horizontal only, `#C5BDB3`, 0.8pt |
| X-axis | Weekly Monday ticks, `DD-Mon`, 45° |
| Y-axis | Comma-formatted integers |
| Legend | Bottom-center, no frame, 3 columns |
| Figure size | 13×5.5 in, 150 dpi |

## Excel style reference

| Element | Value |
|---|---|
| Font | Arial throughout |
| Title | Bold 14pt, left-aligned |
| Header row | White bold Arial 10 on `#2C3E50`, centered, height 30 |
| Data | Arial 10 |
| Output name | `MLU_<period>_QBR.xlsx` or `MLU_<period>_Monthly.xlsx` |

## Notes

- The script auto-discovers all CSVs in each subfolder via glob, so adding a new month's
  file requires no changes — just drop the file in the correct folder.
- Chart PNGs are written to a temporary `charts_tmp/` subfolder and deleted automatically
  after the workbook is saved.
- Apple Podcasts does not expose a subscriber count in its standard analytics export.
  The Followers tab uses **Net Followers** from the Apple Monthly Subscribers export,
  which is the correct metric for follower growth tracking.
