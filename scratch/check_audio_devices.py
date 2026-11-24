import sounddevice as sd

print("Default devices:", sd.default.device)
devices = sd.query_devices()
print(f"Total devices: {len(devices)}")
for i, d in enumerate(devices):
    name = d["name"]
    in_ch = d["max_input_channels"]
    out_ch = d["max_output_channels"]
    sr = d["default_samplerate"]
    if in_ch > 0:
        print(f"  Input  [{i}]: {name} (channels={in_ch}, rate={sr})")
    if out_ch > 0:
        print(f"  Output [{i}]: {name} (channels={out_ch}, rate={sr})")
