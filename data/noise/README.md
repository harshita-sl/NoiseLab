# data/noise — noise assets

Drop noise recordings here (.wav / .flac / .ogg). Use them in conditions by
filename stem, e.g. `noise="kitchen_fan"` for `kitchen_fan.wav`. Files are
looped/trimmed to match the utterance and mixed at exact SNR by
`noiselab.degrade`.

## Sources

1. **Your own recordings** (preferred — you own them): fan, kitchen,
   street, crowd, rain.
2. **License-checked open datasets.** Record the license of each file in
   `LICENSES.md` before committing. Good sources:
   - Freesound (filter CC0)
   - ESC-50 (CC BY-NC — do NOT use for anything public-facing)
   - MUSAN noise subset (Attribution 4.0)

Synthetic noise (`white`, `pink`, `fan`, `traffic`, `babble`) is generated
deterministically in `noiselab.degrade` — always available, no license
needed.
