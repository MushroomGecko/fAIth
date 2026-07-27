# Biblical Map Search Query

The user is studying the Bible and has selected the following text. Generate a search query for a map that best represents the user's selection.

## Full Verse Context
*(Use this only to resolve ambiguity in the Selected Text. Do not let it broaden the query beyond the user's selection.)*

{book} {chapter} ({collection_name})

{verses_text}

## Selected Text

{selected_text}

---

## Task

Generate a single search query for a map based primarily on the Selected Text.

### Instructions

- Identify the geographic subject that best represents the selected text: a place, region, nation, body of water, journey, battle, migration, boundary, people, or historical setting.
- Preserve specific biblical place names and use them in the query whenever possible.
- If the selection does not explicitly mention a place, infer a meaningful map subject from its people, event, movement, or setting.
- If the text concerns tribal territories or inheritance, request a map showing the relevant tribal allotment or territory.
- Include “map” or “biblical map” in the query.
- If no meaningful map subject can be inferred, use exactly: `Biblical map ancient Israel 12 tribes`
- Keep the query concise, normally 2–8 words.

### Output Format

Return only the raw search query. No explanation, punctuation, quotation marks, markdown, or additional text.
