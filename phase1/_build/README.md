# Rebuilding the Phase-1 document

Run from the repository root (needs Node.js, and MS Word for the PDF step):

```bash
cd phase1/_build
npm install                                         # docx library, once
python gen_results_json.py ../..                    # tables from ../../results/*/summary.csv -> results.json
node build.js ../Phase1_G3-09_23I-0746.docx ../.. ..
```

PDF: open the .docx in Word and use File > Save As > PDF, or run
`powershell -ExecutionPolicy Bypass -File render.ps1 -Docx "<full path>\Phase1_G3-09_23I-0746.docx" -Pdf "<full path>\Phase1_G3-09_23I-0746.pdf"`.

Text sources: `content_a.js` (Deliverable A), `content_b.js` (Deliverable B), `results_text.js` (section B.16, results narrative).
After new results: in the repo root run `python scripts/make_report.py --out docs/results`, then the commands above, and
update any numbers quoted in `results_text.js`.
