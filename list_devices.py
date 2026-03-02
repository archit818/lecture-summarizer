import sounddevice as sd
import sys

with open("devices.txt", "w", encoding="utf-8") as f:
    devices = sd.query_devices()
    f.write("Available Audio Devices:\n")
    for i, dev in enumerate(devices):
        try:
            hostapi_info = sd.query_hostapis(dev["hostapi"])
            hostapi_name = hostapi_info["name"]
            f.write(f"[{i}] {dev['name']} (HostAPI: {hostapi_name}, Input Ch: {dev['max_input_channels']}, Output Ch: {dev['max_output_channels']})\n")
        except:
            f.write(f"[{i}] {dev['name']}\n")

    f.write("\nDefault Devices:\n")
    f.write(f"InputStream: {sd.default.device[0]}\n")
    f.write(f"OutputStream: {sd.default.device[1]}\n")
