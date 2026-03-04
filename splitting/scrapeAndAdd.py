import os
import re
import sys
import pandas as pd

scriptDir = os.path.dirname(os.path.abspath(__file__))
outputCsvPath = os.path.join(scriptDir, "Unique Companies.csv")
websiteCol = "Website"

companyColNames = ("Company Name", "Company")


def findCompanyCol(df):
    for col in companyColNames:
        if col in df.columns:
            return col
    for c in df.columns:
        if str(c).strip().lower() in ("company", "company name"):
            return c
    return None


def loadDataFrame(path):
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_excel(path)


def normalize(name):
    if pd.isna(name) or not isinstance(name, str):
        return ""
    s = str(name).strip().lower()
    return re.sub(r"\s+", " ", s)


def main():
    if len(sys.argv) < 2:
        print("  Usage: python scrapeAndAdd.py <input.csv|xlsx>")
        sys.exit(1)

    inputPath = sys.argv[1]
    if not os.path.isfile(inputPath):
        inputPath = os.path.join(scriptDir, inputPath)
    if not os.path.isfile(inputPath):
        print(f"  x Input file not found: {inputPath}")
        sys.exit(1)

    inputDf = loadDataFrame(inputPath)
    inputCompanyCol = findCompanyCol(inputDf)
    if not inputCompanyCol:
        print(f"  x No Company/Company Name column in {inputPath}")
        sys.exit(1)

    allCompanies = {}

    mergePaths = [
        os.path.join(scriptDir, "Unique Companies.csv"),
        os.path.join(scriptDir, "Unique Companies.xlsx"),
    ]
    for path in mergePaths:
        if os.path.isfile(path):
            mergeDf = loadDataFrame(path)
            mergeCompanyCol = findCompanyCol(mergeDf)
            if mergeCompanyCol:
                for _, row in mergeDf.iterrows():
                    company = row.get(mergeCompanyCol)
                    if pd.isna(company):
                        continue
                    orig = str(company).strip()
                    norm = normalize(orig)
                    if not norm:
                        continue
                    web = row.get(websiteCol, "") if websiteCol in mergeDf.columns else ""
                    if pd.notna(web) and str(web).strip().startswith(("http://", "https://")):
                        web = str(web).strip()
                    else:
                        web = None
                    allCompanies[norm] = (orig, web)
            break

    added = 0
    for _, row in inputDf.iterrows():
        company = row.get(inputCompanyCol)
        if pd.isna(company):
            continue
        orig = str(company).strip()
        norm = normalize(orig)
        if not norm:
            continue
        if norm not in allCompanies:
            web = None
            if websiteCol in inputDf.columns:
                w = row.get(websiteCol)
                if pd.notna(w) and str(w).strip().startswith(("http://", "https://")):
                    web = str(w).strip()
            allCompanies[norm] = (orig, web)
            added += 1
        else:
            orig, web = allCompanies[norm]
            if not web and websiteCol in inputDf.columns:
                w = row.get(websiteCol)
                if pd.notna(w) and str(w).strip().startswith(("http://", "https://")):
                    allCompanies[norm] = (orig, str(w).strip())

    rows = [(orig, web or "") for norm, (orig, web) in allCompanies.items()]
    rows.sort(key=lambda x: x[0].lower())

    outDf = pd.DataFrame(rows, columns=["Company Name", websiteCol])
    outDf.to_csv(outputCsvPath, index=False)
    matched = sum(1 for _, w in rows if w)

    print("  Scrape And Add")
    print("  -------------")
    print(f"  Input:     {inputPath}")
    print(f"  Added:     {added}")
    print(f"  Total:     {len(outDf)}")
    print(f"  Websites:  {matched}")
    print(f"  Output:    {outputCsvPath}")


if __name__ == "__main__":
    main()
