# DISPATCH — spec_miner_survey

## Objective
Extract detailed technical specifications, edge cases, format parsing strategies, memory limits, and similarity clustering requirements for document and tabular formats (.pdf, .docx, .pptx, .odt, .csv, .tsv).

## Path to Authoritative Request
`file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md`

## Specific Areas to Investigate
1. Parsing Strategy per Format:
   - PDF: Pure-Python `pypdf.PdfReader` up to 50 pages. What happens if a PDF has >50 pages or is password-protected or corrupted?
   - DOCX: Extract body text from `word/document.xml` using `zipfile` and `xml.etree.ElementTree`. How to extract text nodes (`<w:t>`) cleanly?
   - PPTX: Extract body text from `ppt/slides/slide*.xml` using `zipfile` and XML parsing (`<a:t>`). How to iterate slides in order?
   - ODT: Extract body text from `content.xml` using `zipfile` and XML parsing (`<text:p>`).
   - CSV / TSV: Normalization of tabular data: delimiter sniffing (`csv.Sniffer` or extension-based `,` vs `\t`), reading headers, sorting rows, generating permutation-invariant content digests (e.g. SHA-256 of sorted normalized rows).
2. Similarity & Deduplication Matching:
   - Match type: `CONTENT_NEAR_DUPLICATE` (priority order 50).
   - Exact hash match (normalized text hash) vs near-duplicate token similarity (>= 0.90).
   - What tokenization and similarity metric (Jaccard similarity on word/n-gram tokens, SequenceMatcher, or token set intersection)?
   - Cluster grouping algorithm: union-find / connected components / single-linkage clustering at >= 0.90 similarity.
3. Memory Bounds & Offline Constraints:
   - Memory safe bounds: cap buffer sizes at 25 MB / 50,000 words.
   - 100% offline, zero external network or unauthenticated cloud API calls.
   - Graceful degradation: corrupted / unreadable documents return fallback (e.g. empty string or unmatchable hash) without crashing concurrent processing.

## Deliverable
Write your comprehensive specification report to `file:///home/shubhamshah207/clairvoy/.agents/spec_miner_survey/handoff.md`. Include concrete algorithms, edge cases, error handling, and test case suggestions.

## 2026-09-14T05:43:52Z
You are spec_miner_survey. Your working directory is file:///home/shubhamshah207/clairvoy/.agents/spec_miner_survey. Read file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md and file:///home/shubhamshah207/clairvoy/.agents/spec_miner_survey/DISPATCH.md. Mine detailed format extraction specifications (.pdf, .docx, .pptx, .odt, .csv, .tsv), memory limits, edge cases, and similarity clustering. Report your specification in file:///home/shubhamshah207/clairvoy/.agents/spec_miner_survey/handoff.md and notify me via send_message.
