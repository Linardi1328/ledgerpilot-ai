# Media staging

Use this folder for manually supplied **public-safe demo and product media** that may be implemented later in LedgerPilot AI.

## Good candidates

- Product screenshots and mock dashboard visuals
- Logos, icons, onboarding graphics, and marketing assets
- Fully synthetic sample receipts/invoices/documents created for testing
- Public-safe demo images for document-upload and extraction flows

## Critical data rule

This repository is public. **Never commit real bookkeeping records, bank statements, receipts, invoices, tax files, identity documents, customer files, account numbers, API keys, or other confidential financial/personal data.** Use synthetic or irreversibly anonymized test material only.

## File conventions

- Prefer descriptive lowercase kebab-case filenames.
- Clearly label synthetic test documents, e.g. `synthetic-invoice-retail-01.pdf`.
- Keep originals where practical and avoid duplicate exports.

## Implementation rule

Treat `media/` as staging only. Product code should explicitly copy/process approved assets into the correct frontend `public/` path, test-fixture location, or protected object storage. Real user-uploaded financial documents must use private application storage and must never flow through this repository.
