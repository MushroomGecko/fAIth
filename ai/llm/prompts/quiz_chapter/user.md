## Chapter {chapter} of Book {book} in Version {collection_name}

{verses}

---

## Task

Using only the Biblical chapter and verses provided above, create a multiple-choice quiz for the reader to answer. Every question must pertain directly to this chapter.

## Quiz Guidelines

1. Generate between 1 and 10 questions, depending on how much distinct, unambiguous material the chapter provides.
2. Cover important events, people, teachings, details, and themes from the provided verses.
3. Give each question exactly four options.
4. Use the option keys `a`, `b`, `c`, and `d` exactly once for every question.
5. Make exactly one option correct for each question. The other options should be plausible but incorrect.
6. Set `answer` to the key of the correct option, not to the option's full text.
7. Do not rely on information outside the provided verses.
8. Return only valid JSON. Do not include Markdown, explanations, or code fences.

## Required JSON Structure

Return an object with a `quiz` array. Each item in the array must contain:

- `question`: The quiz question as a string.
- `options`: An object containing string values for exactly `a`, `b`, `c`, and `d`.
- `answer`: One of `a`, `b`, `c`, or `d`, identifying the correct option.

Example shape:

{{
  "quiz": [
    {{
      "question": "Question grounded in the provided chapter?",
      "options": {{
        "a": "First option",
        "b": "Second option",
        "c": "Third option",
        "d": "Fourth option"
      }},
      "answer": "a"
    }}
  ]
}}
