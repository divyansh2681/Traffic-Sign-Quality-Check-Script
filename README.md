# Traffic‑Sign Quality‑Check Script

## What this is?
A tiny command‑line tool that downloads completed Scale AI annotation tasks for a traffic‑sign project, runs a few sanity checks on every bounding‑box label, and writes a JSON report of anything that looks wrong.

## Quick setup
Have Python 3.8+ installed.

## In the project folder run:
pip3 install requests

## Copy your live_… Scale API key and put it in the current shell:
Windows PowerShell : $Env:SCALE_API_KEY = "live_XXXXXXXX"

macOS/Linux bash : export SCALE_API_KEY=live_XXXXXXXX

## Running it:
python3 observe_sign.py --project "Traffic Sign Detection"

A file called quality_issues.json will appear, listing every task that failed at least one check. Add --out some_file.json or --limit 50 if you like.

## What the main files do?
scale_api.py – streams completed tasks from the Scale v1 REST API

checks.py – all the rules (tiny box, wrong colour, duplicates, etc.)

observe_sign.py – glue script: fetch -> check -> write report

quality_issues.json (sample) – example output for the 8 demo tasks

## Reflections:
A file Reflections.txt with the following information:

(a) the checks I wrote 

(b) the check results for each task 

(c) where I would take this with more time
