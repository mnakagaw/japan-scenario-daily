# Public daily site

This folder is a separate public repository. Only publish curated daily content and site assets. The research source is read-only and is never a deployment target. Do not contact research tasks or write back to research files, registries, workflows, or repositories.

Keep the four analysis phases, a concise top summary, a 4000–5000 Japanese-character full report, sources, subjective scenario probabilities, and honest dates. Do not invent initial history or convert null to zero. Same-day Web-to-reference changes and previous-day changes are different measures.

Every news item must display its main countries/regions. New daily news records should include a countries array. Existing editions may use a separate news-labels.json keyed by news ID so published report/data records remain intact. Tag countries actually central to the item, not every country that might be indirectly affected. Use 国際市場 for a global market item with no single country focus.

Before publication, run build.py, validate.py, node --check assets/app.js, and node test-client.cjs. Preserve existing content and publications.json records; append daily entries. Corrections are new records in corrections/ and keep the original text intact. Review the exact staged file list before push. Never add internal receipts, private source material, credentials, user paths, or execution logs.

The user's selected destination is this repository's GitHub Pages. Do not create a separate hosting provider project. Daily content generation runs in the daily task; Actions only validates and publishes static files.
