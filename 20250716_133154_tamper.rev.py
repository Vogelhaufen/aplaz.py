# Auto-scraped Python code
input_file = "broken.sql"
output_file = "fixed.sql"

with open(input_file, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

# Re-encode broken mojibake assuming it was UTF-8 misread as Latin1
fixed = content.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")

with open(output_file, "w", encoding="utf-8") as f:
    f.write(fixed)

print(f"✅ Encoding fix complete. Saved as {output_file}.")