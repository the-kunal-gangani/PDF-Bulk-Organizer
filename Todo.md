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