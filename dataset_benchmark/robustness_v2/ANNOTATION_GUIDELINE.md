# Annotation Guideline

## General rules

Annotators must judge only the supplied evidence, keep Vietnamese diacritics,
and never infer missing gold pages or scores. Leave a field blank and add a note
when evidence is insufficient. Mark a row reviewed only after every required
field is completed.

## Transcript error and recoverability

Compare the reference, raw STT, and corrected text. Assign the documented error
taxonomy to the smallest meaningful span. Mark correction outcome as improved,
unchanged, or degraded. Recoverability is `text_recoverable` only when the
intended content can reasonably be reconstructed from the raw 1-best text;
otherwise use `audio_only` or `uncertain`. Do not use the corrected output to
retroactively assume recoverability.

## Retrieval relevance

Gold relevance must be judged against the user intent and page content, not
against the pages returned by the reference-query run. Record source and page
identifiers exactly. Reference-query overlap is a diagnostic proxy and must not
be copied into gold labels.

## Final-answer comparison

Blind the pipeline identity. Grade correctness, groundedness, completeness,
helpfulness, and safety using the same evidence for all candidates, then record
preference or tie plus a concise rationale. Human judgment is primary; an LLM
judge, if later enabled, is auxiliary and may not overwrite human labels.

## Adjudication and quality control

Two raters annotate independently. Resolve disagreements in a separate
adjudication pass while retaining both original ratings. Validate identifiers,
required columns, allowed values, duplicate rows, and UTF-8 text before export.
Every consumed workbook must be captured by path, SHA-256, and byte size.
