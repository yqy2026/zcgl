# Document Extraction

## Status
Current implementation: RapidOCR and PyMuPDF produce local page text; DeepSeek is an optional text-only enrichment stage. Every extracted value is reviewed by a user before confirmation.

## API
- Contract sessions: `/api/v1/extraction-sessions/contracts`
- Property certificate sessions: `/api/v1/extraction-sessions/property-certificates`
- Generic property certificate attachments: `/api/v1/property-certificates/{certificate_id}/attachments`

## Flow
1. Stage one PDF or image.
2. Create an extraction session and review the candidate fields.
3. Correct fields or select an explicit conflict action.
4. Confirm the session; the API either creates the approved record or links the approved existing record.

No legacy PDF import, batch-import, vision-provider, or Prompt-management endpoints remain.
## Limits
Contracts accept one PDF up to 50 MiB and 50 pages. The local page-text pipeline keeps page order and processes pages sequentially; optional DeepSeek enrichment sends text-only batches of up to 20 pages and returns one combined candidate set only when every batch validates. Property-certificate PDFs remain limited to 20 pages. All candidates still require manual review before confirmation.