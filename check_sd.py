import sounddevice as sd
import inspect

print(f"Sounddevice version: {sd.__version__}")
try:
    print(f"WasapiSettings arguments: {inspect.signature(sd.WasapiSettings.__init__)}")
except Exception as e:
    print(f"Could not get signature: {e}")
    print(f"WasapiSettings dir: {dir(sd.WasapiSettings)}")
