import os
import re

src_dir = r"d:\Zye\external_mcp\spotify-mcp-server\src"

for fname in os.listdir(src_dir):
    if not fname.endswith(".ts"):
        continue
    fpath = os.path.join(src_dir, fname)
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    # Find returns that return an Error text in content array without top-level isError
    # e.g.:
    # return {
    #   content: [
    #     {
    #       type: 'text',
    #       text: `Error...`
    #     },
    #   ],
    # };
    def fix_block(match):
        block = match.group(0)
        if "isError" in block:
            return block
        # Replace the end of the content array `],` or `]` before `};` with `],\n        isError: true,`
        last_bracket = block.rfind("]")
        if last_bracket != -1:
            after = block[last_bracket + 1 :]
            # Check if there's already isError
            if "isError" in after:
                return block
            return block[: last_bracket + 1] + ",\n        isError: true," + after
        return block

    # Match return statements that contain Error text
    pattern = re.compile(
        r"return\s*\{\s*content:\s*\[\s*\{\s*type:\s*['\"]text['\"],\s*text:\s*[`'\"](?:Error|Failed)[^`'\"]*[`'\"](?:,\s*isError:\s*true)?\s*\}\s*\]\s*\}\;",
        re.DOTALL,
    )
    new_content = pattern.sub(fix_block, content)

    if new_content != content:
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Fixed error returns in {fname}")

print("Done scanning and fixing isError.")
