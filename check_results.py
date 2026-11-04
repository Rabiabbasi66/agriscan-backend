import csv, os
CSV_PATH = "agriscan_model/classification_v1/results.csv"
print("="*60)
print("AGRISCAN 3D - RESULTS CHECK")
print("="*60)
with open(CSV_PATH) as f:
    rows = list(csv.reader(f))
print(f"\nTotal lines (with header): {len(rows)}")
print(f"Total epochs completed: {len(rows)-1}")
print(f"\nHeader: {rows[0]}")
print("\n--- ALL EPOCHS ---")
for r in rows[1:]:
    print(r)
last = rows[-1]; header = rows[0]
print("\n--- LAST EPOCH (FINAL METRICS) ---")
for h,v in zip(header,last):
    print(f"  {h}: {v}")
print("\n--- FOLDER CONTENTS ---")
for x in os.listdir("agriscan_model/classification_v1"):
    print("  "+x)
print("\n--- WEIGHTS ---")
for x in os.listdir("agriscan_model/classification_v1/weights"):
    print("  "+x)
