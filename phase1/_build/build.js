// Builds Phase1_G3-09_23I-0746.docx. Usage: node build.js <outPath> <repoDir>
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, ImageRun, PageBreak, PageOrientation, LevelFormat, Footer,
  PageNumber, TabStopType, TableLayoutType, VerticalAlign,
} = require('docx');
const A = require('./content_a');
const B = require('./content_b');

const OUT = process.argv[2];
const REPO = process.argv[3];
const RES = fs.existsSync(path.join(__dirname, 'results.json')) ? JSON.parse(fs.readFileSync(path.join(__dirname, 'results.json'), 'utf8')) : null;
const RT = fs.existsSync(path.join(__dirname, 'results_text.js')) ? require('./results_text') : null;

const FONT = 'Times New Roman';
const PORTRAIT_W = 9026;   // A4 width 11906 - 2 x 1440
const LAND_W = 14678;      // A4 height 16838 - 2 x 1080
let figNo = 0, tabNo = 0;

// --- inline markup: **bold**, *italic*
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith('**')) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}
const P = (text, opt = {}) => new Paragraph({ children: runs(text, opt.run || {}), alignment: opt.align || AlignmentType.JUSTIFIED,
  spacing: { after: opt.after ?? 120, line: 264 }, ...(opt.para || {}) });
const LP = (label, text) => new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 80, line: 264 },
  children: [new TextRun({ text: label + ' ', bold: true }), ...runs(text)] });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)], spacing: { before: 240, after: 160 }, keepNext: true });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)], spacing: { before: 200, after: 100 }, keepNext: true });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)], spacing: { before: 160, after: 60 }, keepNext: true });
const BUL = (text) => new Paragraph({ numbering: { reference: 'bul', level: 0 }, alignment: AlignmentType.JUSTIFIED,
  spacing: { after: 60, line: 264 }, children: runs(text) });
const NUM = (text, ref = 'num') => new Paragraph({ numbering: { reference: ref, level: 0 }, alignment: AlignmentType.JUSTIFIED,
  spacing: { after: 60, line: 264 }, children: runs(text) });
const BRK = () => new Paragraph({ children: [new PageBreak()] });
const caption = (kind, text) => {
  const n = kind === 'Figure' ? ++figNo : ++tabNo;
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 180 }, keepNext: kind === 'Table',
    children: [new TextRun({ text: `${kind} ${n}. `, bold: true, size: 20 }), ...runs(text, { size: 20 })] });
};
const border = { style: BorderStyle.SINGLE, size: 4, color: '999999' };
function table(headers, rows, widths, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const size = opts.size || 18;
  let keep = false;
  const cell = (t, w, head, shade) => new TableCell({
    width: { size: w, type: WidthType.DXA }, verticalAlign: VerticalAlign.TOP,
    borders: { top: border, bottom: border, left: border, right: border },
    shading: head ? { type: ShadingType.CLEAR, color: 'auto', fill: 'D9E2F3' } : (shade ? { type: ShadingType.CLEAR, color: 'auto', fill: 'FFF2CC' } : undefined),
    margins: { top: 50, bottom: 50, left: 80, right: 80 },
    children: [new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 0, line: 240 }, keepNext: keep,
      children: runs(String(t), { size, bold: head || undefined }) })],
  });
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths, layout: TableLayoutType.FIXED,
    // short tables are kept on one page (keepNext on every row but the last)
    rows: [new TableRow({ tableHeader: true, children: headers.map((h, i) => { keep = rows.length <= 14; return cell(h, widths[i], true); }) }),
      ...rows.map((r, ri) => new TableRow({ cantSplit: true, children: r.map((c, i) => { keep = rows.length <= 14 && ri < rows.length - 1; return cell(c, widths[i], false, opts.shadeRow && opts.shadeRow(r, ri)); }) }))],
  });
}
function figure(file, widthPx, captionText) {
  if (!fs.existsSync(file)) return [P(`[Missing figure: ${path.basename(file)}]`), caption('Figure', captionText)];
  const buf = fs.readFileSync(file);
  // PNG size from header
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  return [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 40 }, keepNext: true,
    children: [new ImageRun({ type: 'png', data: buf, transformation: { width: widthPx, height: Math.round(widthPx * h / w) },
      altText: { title: captionText || path.basename(file), description: captionText || path.basename(file), name: path.basename(file) } })] }),
  ...(captionText ? [caption('Figure', captionText)] : [])];
}
function placeholderBox(lines) {
  return new Table({ width: { size: PORTRAIT_W, type: WidthType.DXA }, columnWidths: [PORTRAIT_W], rows: [new TableRow({ children: [
    new TableCell({ width: { size: PORTRAIT_W, type: WidthType.DXA }, shading: { type: ShadingType.CLEAR, color: 'auto', fill: 'F2F2F2' },
      borders: { top: border, bottom: border, left: border, right: border }, margins: { top: 300, bottom: 300, left: 200, right: 200 },
      children: lines.map((l, i) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
        children: [new TextRun({ text: l, italics: i > 0, bold: i === 0, color: '7F7F7F' })] })) })] })] });
}

// ---------------- title page
const team = [['Fatima Khursheed', '23I-0746', 'Group head'], ['Saleha Muhammad', '23I-0727', 'Member']];
const titlePage = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 600, after: 120 }, children: [new TextRun({ text: 'National University of Computer and Emerging Sciences (FAST), Islamabad', size: 24 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 }, children: [new TextRun({ text: 'AI4015 Agentic Artificial Intelligence — Fall 2026', size: 24 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: 'Semester Project — Phase 1', bold: true, size: 32 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 }, children: [new TextRun({ text: 'Literature Review, Research Gaps, Proposal & Baseline', size: 26 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: 'Project code: G3-09', bold: true, size: 26 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: 'Seed: EMI-RAPL — Trustworthy Mechatronics and Robotics Intelligence through Reasoning Agentic LLMs and Physics-Informed Learning', italics: true, size: 22 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 240, after: 600 }, children: [new TextRun({ text: B.TITLE, bold: true, size: 30 })] }),
  table(['Name', 'Roll number', 'Role'], team, [3600, 2400, 3026], { size: 22 }),
  new Paragraph({ spacing: { before: 400, after: 80 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Supervisor: Naeem Tareen    |    Instructor: Muhammad Owais Idrees', size: 22 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [new TextRun({ text: 'GitHub (Deliverable C): https://github.com/Fatima-Khursheed20/emi-rapl-thermal', size: 22 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'October 2026', size: 22 })] }),
  BRK(),
];

// ---------------- Deliverable A
const delA = [H1('Deliverable A — Literature Review and Research Gaps'), H2('A.1 Paper selection'), ...A.SELECTION.map((t) => P(t))];
delA.push(H2('A.2 Base paper'));
delA.push(P(`**Reference.** ${A.REFS[0]}`));
delA.push(P('**Proof of ranking.** *Journal of Process Control* (Elsevier, ISSN 0959-1524) has a 2025 SCImago Journal Rank (based on Scopus) of **0.874, Q1**, with an h-index of 138 [19]. In 2025 it is **Q1 in Control and Systems Engineering, in Industrial and Manufacturing Engineering and in Modeling and Simulation**, and Q2 in Computer Science Applications. The guideline accepts a Q1 ranking in Scopus or JCR, so the base paper is eligible. Figure 1 shows the SCImago record.'));
const PH1 = process.argv[4];
delA.push(...figure(path.join(PH1, 'figures', 'scimago_sjr2025.png'), 330, null));
delA.push(...figure(path.join(PH1, 'figures', 'scimago_quartiles.png'), 520, 'SCImago Journal Rank record of *Journal of Process Control* [19]: (top) subject categories and 2025 SJR of 0.874 in quartile Q1; (bottom) quartile history by category, with 2025 in Q1 for Control and Systems Engineering, Industrial and Manufacturing Engineering and Modeling and Simulation (green = Q1, yellow = Q2).'));
delA.push(H3('Why this paper was selected'));
A.BASE.why.forEach((t) => delA.push(BUL(t)));
delA.push(H3('Problem, method, data and results'));
delA.push(LP('Problem.', A.BASE.problem), LP('Method and agent architecture.', A.BASE.method), LP('Dataset / benchmark.', A.BASE.data), LP('Key results.', A.BASE.results));
delA.push(H3('Limitations stated by the authors'));
A.BASE.limAuthors.forEach((t) => delA.push(BUL(t)));
delA.push(H3('Limitations identified by our group'));
A.BASE.limOurs.forEach((t) => delA.push(BUL(t)));
delA.push(H3('How our project builds on, compares against and goes beyond it'));
delA.push(P(A.BASE.beyond));

delA.push(H2('A.3 Critical summaries of the reviewed papers'));
delA.push(P('Each summary covers the problem, method, data, results, limitations (author-stated and our own) and relevance to our project.'));
for (const [title, s] of A.SUMMARIES) {
  delA.push(H3(title));
  delA.push(LP('Problem.', s.problem), LP('Method.', s.method), LP('Data.', s.data), LP('Results.', s.results), LP('Limitations.', s.limitations), LP('Relevance.', s.relevance));
}

const landTable = [
  H2('A.4 Cross-paper comparison'),
  P('Table 1 summarises all reviewed papers; the base paper is marked with ★ and highlighted.', { after: 80 }),
  caption('Table', 'Cross-paper comparison of the twelve reviewed papers (★ = base paper).'),
  table(['#', 'Title (short)', 'Year & venue', 'Dataset / benchmark', 'Method / agent architecture', 'Evaluation metrics', 'Key results', 'Limitations / research gap'],
    A.TABLE, [520, 1650, 1450, 1750, 2500, 1900, 2350, 2558], { size: 18, shadeRow: (r) => r[0].includes('★') }),
];

const gapsSec = [
  H2('A.5 Research gap synthesis'),
  P(A.GAPS_INTRO),
  caption('Table', 'Candidate research gaps identified from the review.'),
  table(['Gap', 'Description', 'Evidence'], A.CANDIDATES, [1500, 5526, 2000], { size: 18, shadeRow: (r) => r[0].includes('selected') }),
  P('', { after: 60 }),
  P('The three selected gaps are specific (each names one mechanism), evidence-based (each is supported by named papers above), relevant (each is a limitation of the base workflow) and testable (each has a metric we can compute on our plant this semester). G4–G6 are real but either outside the semester\'s scope (G6) or handled as part of our methodology rather than as a contribution (G4 is measured as latency; G5 is addressed by repeats, confidence intervals and non-LLM baselines).'),
  caption('Table', 'Selected research gaps.'),
  table(['Gap', 'Supporting evidence (papers)', 'Proposed approach', 'How it will be measured'], A.GAP_TABLE, [2000, 2300, 2626, 2100], { size: 17 }),
];

// ---------------- Deliverable B
const delB = [BRK(), H1('Deliverable B — Project Proposal')];
delB.push(H2('B.1 Project title and selected seed'), P(`**Title:** ${B.TITLE}.`), ...B.SEED.map((t) => P(t)));
delB.push(H2('B.2 Problem statement and motivation'), ...B.PROBLEM.map((t) => P(t)));
delB.push(H2('B.3 Base paper and research gaps'), ...B.BASE_GAPS.map((t) => P(t)));
delB.push(H2('B.4 Target product or system'), ...B.TARGET.map((t) => P(t)), ...B.TARGET_BULLETS.map((t) => BUL(t)));
delB.push(H2('B.5 Agentic justification'), P('The problem needs agentic behaviour rather than a deterministic workflow, a single LLM call or a simple RAG pipeline, for five reasons:'));
B.AGENTIC.forEach(([a, b]) => delB.push(BUL(`**${a}** ${b}`)));
delB.push(H2('B.6 Goals and success criteria'), H3('Development objectives'));
B.DEV_OBJ.forEach((t) => delB.push(NUM(t)));
delB.push(H3('Research objectives and success criteria'), caption('Table', 'Success criteria, one or more per gap.'), table(['Gap', 'Success criterion'], B.SUCCESS, [900, 8126], { size: 19 }));
delB.push(H2('B.7 Data, environment and source'), ...B.DATA.map((t) => P(t)),
  caption('Table', 'Fault library of the evaluation environment.'),
  table(['Fault', 'Class', 'Injected effect (range)', 'Consequence without recovery'], B.FAULTS, [2000, 1100, 3326, 2600], { size: 18 }),
  P('', { after: 40 }), ...B.DATA2.map((t) => P(t)));
delB.push(H2('B.8 System architecture'), caption('Table', 'System architecture components.'), table(['Component', 'Design'], B.ARCH, [1800, 7226], { size: 18 }));
delB.push(H2('B.9 Methodology and architecture diagram'), P(B.DIAGRAM_TEXT),
  ...figure(path.join(REPO, 'docs', 'architecture.png'), 610, 'System architecture. Blue: base-paper workflow (baseline); orange: proposed components for gaps G1–G3 (dashed lines are new data flows); grey: deterministic modules; purple: human control.'));
delB.push(H2('B.10 Baselines'), caption('Table', 'Baselines.'), table(['Baseline', 'Description'], B.BASELINES, [2000, 7026], { size: 18 }));
delB.push(H2('B.11 Research questions and hypotheses'), caption('Table', 'Research question and testable prediction per gap.'), table(['Gap', 'Research question', 'Hypothesis'], B.RQ, [800, 4626, 3600], { size: 18 }));
delB.push(H2('B.12 Evaluation plan'), caption('Table', 'Evaluation plan.'), table(['Item', 'Plan'], B.EVAL, [1800, 7226], { size: 18 }));
delB.push(H2('B.13 Milestones and feasibility'), caption('Table', 'Milestones.'), table(['Stage', 'Work'], B.MILESTONES, [2200, 6826], { size: 18 }),
  P('', { after: 40 }), caption('Table', 'Technical risks and fallback strategies.'), table(['Risk', 'Mitigation / fallback'], B.RISKS, [3200, 5826], { size: 18 }),
  P('Compute is modest: the simulator runs at about 4,000 steps per second on a laptop CPU, so an episode takes roughly one second without LLM calls. The binding constraint is the LLM quota, which the pacer and subset design keep within free-tier limits.'));
delB.push(H2('B.14 Work division'), caption('Table', 'Responsibilities.'), table(['Member', 'Responsibilities'], B.WORK, [2800, 6226], { size: 18 }));
delB.push(H2('B.15 Potential publication direction'), ...B.PUBLICATION.map((t) => P(t)));

// ---------------- Technical foundation + initial results (Deliverable C summary)
const techSec = [H2('B.16 Technical foundation and initial baseline results (Deliverable C)')];
if (RT) {
  RT.INTRO.forEach((t) => techSec.push(P(t)));
  if (RES) {
    techSec.push(caption('Table', RT.TABLE1_CAPTION));
    techSec.push(table(RES.full.headers, RES.full.rows, RES.full.widths, { size: 17 }));
    techSec.push(P('', { after: 40 }));
    RT.AFTER_TABLE1.forEach((t) => techSec.push(P(t)));
    techSec.push(...figure(path.join(REPO, 'docs', 'results', 'fig_validated_but_failed.png'), 470, RT.FIG_VBF));
    techSec.push(caption('Table', RT.TABLE2_CAPTION));
    techSec.push(table(RES.llm.headers, RES.llm.rows, RES.llm.widths, { size: 17 }));
    techSec.push(P('', { after: 40 }));
    RT.AFTER_TABLE2.forEach((t) => techSec.push(P(t)));
    techSec.push(...figure(path.join(REPO, 'docs', 'results', 'fig_llm_subset_plant_success.png'), 470, RT.FIG_LLM));
    RT.CASES.forEach((t) => techSec.push(BUL(t)));
    RT.CLOSING.forEach((t) => techSec.push(P(t)));
  }
} else {
  techSec.push(P('[Initial results are inserted here once the evaluation runs finish.]'));
}

// ---------------- references
const refs = [H1('References'), ...A.REFS.map((r, i) => new Paragraph({ spacing: { after: 60, line: 252 }, indent: { left: 540, hanging: 540 },
  tabStops: [{ type: TabStopType.LEFT, position: 540 }], children: [new TextRun({ text: `[${i + 1}]\t`, size: 20 }), ...runs(r, { size: 20 })] }))];

const footer = new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
  new TextRun({ text: 'G3-09 · Phase 1 · page ', size: 18, color: '7F7F7F' }), new TextRun({ children: [PageNumber.CURRENT], size: 18, color: '7F7F7F' })] })] });
const portrait = { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } };
const landscape = { page: { size: { width: 11906, height: 16838, orientation: PageOrientation.LANDSCAPE }, margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 } } };

const doc = new Document({
  creator: 'Fatima Khursheed; Saleha Muhammad', title: `Phase 1 — G3-09 — ${B.TITLE}`,
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 30, bold: true, font: FONT, color: '1F3864' }, paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 26, bold: true, font: FONT, color: '2F5496' }, paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 23, bold: true, font: FONT }, paragraph: { spacing: { before: 160, after: 60 }, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [
    { reference: 'bul', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    { reference: 'num', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
  ] },
  sections: [
    { properties: portrait, children: titlePage },
    { properties: portrait, footers: { default: footer }, children: delA },
    { properties: landscape, footers: { default: footer }, children: landTable },
    { properties: portrait, footers: { default: footer }, children: [...gapsSec, ...delB, ...techSec, ...refs] },
  ],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log('wrote', OUT, buf.length, 'bytes; figures', figNo, 'tables', tabNo); });
