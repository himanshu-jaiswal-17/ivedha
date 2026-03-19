#!/usr/bin/env python3
# Reads the sales data CSV and outputs a new file containing only
# properties sold below the average price per square foot.
# No external dependencies - uses stdlib csv module.

import csv
import os
import sys


def main():
    input_file = os.getenv("INPUT_CSV", "Assignment_python.csv")
    output_file = os.getenv("OUTPUT_CSV", "filtered_below_avg_price_per_sqft.csv")

    # read all rows and calculate price per sqft where possible
    valid_rows = []

    try:
        with open(input_file, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

            for row in reader:
                try:
                    price = float(row["price"])
                    sq_ft = float(row["sq__ft"])
                    if sq_ft > 0:
                        row["_price_per_sqft"] = price / sq_ft
                        valid_rows.append(row)
                except (ValueError, ZeroDivisionError, KeyError):
                    continue  # skip bad rows

    except FileNotFoundError:
        print(f"ERROR: '{input_file}' not found.")
        sys.exit(1)

    if not valid_rows:
        print("ERROR: no valid records found.")
        sys.exit(1)

    # average price per sqft
    avg = sum(r["_price_per_sqft"] for r in valid_rows) / len(valid_rows)
    print(f"Total valid records    : {len(valid_rows)}")
    print(f"Average price / sq ft  : ${avg:.2f}")

    # filter rows below average and write output
    filtered = [r for r in valid_rows if r["_price_per_sqft"] < avg]

    output_fieldnames = list(fieldnames) + ["price_per_sqft"]

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in filtered:
            row["price_per_sqft"] = f"{row['_price_per_sqft']:.2f}"
            writer.writerow(row)

    print(f"Filtered records       : {len(filtered)}")
    print(f"Output written to      : {output_file}")


if __name__ == "__main__":
    main()
