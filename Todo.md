A bunch of directions we could take this — happy to build any of these next:

## Visual/UX polish
- **Drag-and-drop folder support** — drag a folder straight onto the window instead of typing/browsing
- **Category filter chips** — checkboxes to only show Invoice/Resume/etc. in the log, hide the rest
- **Summary chart** at the end — a small bar showing "5 Invoices, 3 Resumes, 2 Unsorted" instead of just a scroll of lines
- **Dark/light theme toggle** button in the header
- **Undo button** — reverse the last "Organize" run using the log file, move everything back

## Functional upgrades
- **OCR support** for scanned PDFs with no extractable text (`pytesseract`) — right now those always land in Unsorted
- **Custom category editor** — a settings panel where you add/edit keywords per category without touching code
- **Recent folders** dropdown — remembers the last few folders you've pointed it at
- **Duplicate detection** — flag PDFs that look identical (same hash) instead of just renaming both
- **Export summary report** — a PDF or CSV summary of what got organized, timestamps and all

## "Show off on resume" upgrades
- **Batch processing progress %** — "Processing file 6 of 42" instead of just a spinning bar
- **Config file support** (`config.yaml`) — categories/keywords defined outside code, more "production tool" feeling
- **Packaging as a `.exe`** using PyInstaller, so it's a real double-click desktop app, not "run this Python script"

My pick if you want the highest-impact next step: **OCR support** (handles a whole class of files it currently can't) + **packaging as a .exe** (turns it from "a script" into "an actual app you can hand someone"). Those two together make it a much stronger portfolio piece.

Want me to start with one of these?

We've built out basically the entire feature wishlist at this point. Here's what's left on the table:

## Finish the product
- **📦 Package as a `.exe`** — the one we deliberately held off on. Now that everything's built and tested, this is probably the natural "final" step to make it a real double-click app
- **Drag-and-drop folder support** — drag a folder straight onto the window instead of Browse/Recent dropdown
- **Scoring weights in the editor** — right now strong/weak/exclude are editable, but the scoring numbers (strong_weight, threshold, etc.) still need manual YAML editing

## Polish / documentation
- **Updated README** for GitHub reflecting all the new features (OCR, undo, duplicates, config editor, GUI)
- **Updated project structure / resume blurb** — this project now has way more depth than the original CV bullet we wrote weeks ago

## Testing
- Try it on your actual real messy PDF folder end-to-end with everything (OCR + config editor + duplicates + undo) to catch any real-world edge case we haven't hit in synthetic tests

My honest take: this project is genuinely feature-complete now. I'd suggest **packaging as `.exe`** next since that's the step that turns it from "a very solid Python tool" into "a finished, shareable product" — and then updating the README/resume framing to reflect everything it does now.

Want to go with that, or something else first?