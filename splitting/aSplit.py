import math
import os
import re
import sys
import csv
import pandas as pd

sheetName = 0
rowsPerFile = 50
outputPrefix = "Full_CW_Speaker_List_part"
outputDir = "splt"


def normalizeCompany(name):
    if pd.isna(name) or not isinstance(name, str):
        return ""
    s = str(name).strip().lower()
    return re.sub(r"\s+", " ", s)


def splitExcelToCsv(inputPath):
    df = pd.read_excel(inputPath, sheet_name=sheetName)
    df = df.replace(",", " ", regex=True)

    totalRows = len(df)
    if totalRows == 0:
        print("  Split")
        print("  -----")
        print("  No rows found in the Excel sheet.")
        return

    numParts = math.ceil(totalRows / rowsPerFile)
    baseDir = os.path.dirname(os.path.abspath(inputPath))
    outDir = os.path.join(baseDir, outputDir)
    os.makedirs(outDir, exist_ok=True)

    for i in range(numParts):
        start = i * rowsPerFile
        end = min((i + 1) * rowsPerFile, totalRows)
        partDf = df.iloc[start:end]
        outName = f"{outputPrefix}_{i + 1}.csv"
        outPath = os.path.join(outDir, outName)
        partDf.to_csv(outPath, index=False, sep=",", quoting=csv.QUOTE_NONE)

    print("  Split")
    print("  -----")
    print(f"  File:      {inputPath}")
    print(f"  Rows:      {totalRows}")
    print(f"  Parts:     {numParts}")
    print(f"  OutputDir: {outDir}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("  Usage: python aSplit.py <input.xlsx>")
        sys.exit(1)

    inputPath = sys.argv[1]
    if not os.path.isfile(inputPath):
        print(f"  x Input file not found: {inputPath}")
        sys.exit(1)

    splitExcelToCsv(inputPath)

