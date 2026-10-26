"""Record the Bolta Khata demo video by driving the real Streamlit app.

Drives headless Chrome (system binary) through the actual UI. All audio
used is pre-rendered eval clips whose transcripts are disk-cached, so
recording spends ~0 API calls (read-back TTS may cost ~2 calls).

Output: outputs/demo/raw.webm  (video only — narration muxed separately)
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "demo"
APP = "http://localhost:8501"

CLIPS = ROOT / "outputs" / "audio_cmd"


def settle(page, s=2.0):
    page.wait_for_timeout(int(s * 1000))


def upload_and_process(page, wav: str, expect: str):
    page.get_by_text("📁 Upload").click()
    settle(page, 1)
    page.set_input_files('input[type="file"]', str(wav))
    settle(page, 2.5)
    page.get_by_role("button", name="Suno + samjho").click()
    page.wait_for_selector(f"text={expect}", timeout=60000)
    page.locator(f"text={expect}").last.scroll_into_view_if_needed()
    settle(page, 4)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=str(OUT), record_video_size={
                "width": 1280, "height": 800})
        page = ctx.new_page()

        # ---- scene 0: load + reset to a clean ledger
        page.goto(APP)
        page.wait_for_selector("text=Counter", timeout=30000)
        settle(page, 3)
        page.get_by_text("Reset demo data").click()
        page.wait_for_selector("text=Counter", timeout=30000)
        settle(page, 3)

        # ---- scene 1: NOISY command that gets refused (the catch)
        upload_and_process(page, CLIPS / "hg03" / "babble_5.wav",
                           "mein ji")
        settle(page, 5)

        # ---- scene 2: same command, clean -> instant stock answer
        upload_and_process(page, CLIPS / "hg03" / "clean.wav",
                           "maggie kitani")
        settle(page, 5)

        # ---- scene 3: payment -> confirm card -> Haan -> write
        upload_and_process(page, CLIPS / "hg01" / "clean.wav",
                           "rahul ne paanch")
        settle(page, 2)
        page.get_by_role("button", name="Haan, likh do").click()
        page.locator("text=Likha gaya").scroll_into_view_if_needed()
        settle(page, 6)

        # ---- scene 4: Khata page — entry + balance visible
        page.get_by_label("page", exact=False)  # radio group exists
        page.locator("label", has_text="Khata").click()
        settle(page, 4)

        # ---- scene 5: undo
        page.get_by_role("button", name="Undo last entry").click()
        settle(page, 4)

        # ---- scene 6: the chart (file URL)
        page.goto("file://" + str(ROOT / "outputs" / "results"
                                    / "command_eval.png"))
        settle(page, 5)

        ctx.close()
        browser.close()
    print("video recorded into", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
