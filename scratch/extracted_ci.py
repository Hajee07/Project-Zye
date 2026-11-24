import json
from pathlib import Path

full_transcript = Path("C:/Users/Hajzzy/.gemini/antigravity/brain/1583288c-cc38-4dd4-94ff-fa1e40492d72/.system_generated/logs/transcript_full.jsonl")

with open(full_transcript, "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        if "computer_intelligence_mcp.py" in line and ("write_file" in line or "edit_file" in line or "Created file" in line):
            print(f"Index {idx}: {line[:120]}")
            data = json.loads(line)
            # check if there's Content or replacement
            s = json.dumps(data)
            if "inspect_dataset_schema" in s and "get_dataset_analysis_report" in s:
                print(f"===> MATCH WITH ALL TOOLS at index {idx}!")
                # Let's inspect data
                # It might be in tool_calls or arguments
                for k, v in data.items():
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict):
                                for subk, subv in item.items():
                                    if isinstance(subv, dict) and "Content" in subv:
                                        print(f"Found Content in {subk}: length {len(subv['Content'])}")
                                        with open("d:/Zye/scratch/extracted_ci.py", "w", encoding="utf-8") as out:
                                            out.write(subv["Content"])
                                        print("Wrote to d:/Zye/scratch/extracted_ci.py")
