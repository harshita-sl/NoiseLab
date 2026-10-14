from pathlib import Path
from dotenv import load_dotenv
from gnani.tts import GnaniTTSClient

load_dotenv()
out = Path("outputs")
out.mkdir(exist_ok=True)

client = GnaniTTSClient()
audio = client.synthesize(
    "राहुल ने आज पाँच सौ रुपये दिए।", 
    voice="Asmita",
    model="timbre-v2.5",
    language="hi-IN",
    )
(out / "hello.wav").write_bytes(audio)
print("saved", len(audio), "bytes")