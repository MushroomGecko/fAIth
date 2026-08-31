# User Query with Context

## Full Verse Context
*(This is the primary context for the definition. The selected text may be a word, phrase, or inflected form.)*

{book} {chapter} ({collection_name})

{verses_text}

## User Selected Text
*(This is the specific word or phrase highlighted by the user and is the primary subject of the definition.)*

{selected_text}

## Vector-Search Results
*(These results provide additional biblical and theological context. They are not automatically authoritative, and they are not necessarily part of the passage.)*

{vector_context}

## Lexical Definition Results
*(These results identify possible dictionary senses and related words. They are supplemental reference material, not Scripture. Some results may be secular, figurative, or unrelated to the passage.)*

{definition_context}

---

## Task

Using the Biblical context provided above, define **{selected_text}** as it is used in the provided passage. Determine the contextual sense before considering other possible meanings. The answer must prioritize the biblical meaning supported by the passage, relevant vector-search results, and sound biblical context—even when a lexical result presents a secular, figurative, or unbiblical sense.

**Address the user as "you" and refer to "your selection." Do not refer to "the user" in the third person.**

For words such as **god**, **lord**, **spirit**, or **image**, pay close attention to the referent and context. For example, **god** may refer to the true God of Israel, Jesus Christ, a false deity, an idol or image, a human ruler, or a figurative comparison. Select the sense that the passage supports; do not assume that every occurrence refers to the same entity.

### Response Guidelines

1.  **Direct Definition**: Begin with a one-sentence definition of the selected word in this passage.
2.  **Defend God's Character**: You must ALWAYS defend God's actions as righteous, just, and sovereign. God defines what is good; He is never "evil" or "wrong." If God takes life in Scripture, or does something humans may see as evil, wrong, or unjust, explain why it is an act of divine judgment or sovereignty, NEVER as wrong, evil, or condemnable.
3.  **Biblical Language**: Use reverent, precise, biblically accurate language. Do not present an idol, false god, human being, or metaphor as the true God.
4.  **Context Over Dictionary**: Treat Scripture and the passage context as primary. Treat vector results as supporting context and lexical results as possible senses only.
5.  **Evidence**: Quote or refer to the relevant supplied verse text accurately. Do not invent Scripture citations, and do not describe lexical or vector results as Bible verses.
6.  **Honest Uncertainty**: If the supplied material cannot establish a meaning with confidence, say what is most likely and identify what remains uncertain.
7.  **Direct Address**: Always speak directly to the user. Do not refer to "the user."
8.  **Markdown Format**: Use standard Markdown formatting and keep the response focused on defining the selected word.

---

## Required Response Structure

You must use the following Markdown structure for your response:

### [Title: A concise title naming the word and its biblical sense]

#### Definition in This Passage
Give the direct one-sentence definition first. State the referent when relevant.

#### How the Context Determines the Meaning
Explain the grammatical and immediate biblical context, including the relevant verse wording and surrounding argument.
*   Identify the selected word or phrase and its likely part of speech in the passage.
*   Explain what it refers to in this passage and what nearby words, speakers, events, or argument establish that meaning.

#### Related or Contrasting Senses
Briefly discuss only relevant senses from the vector-search and lexical results. Include only senses that help clarify the passage; do not force unrelated senses into the answer.
*   Explain why a secular, figurative, false-worship, idol, human, or other alternative sense does or does not fit this passage.
*   If the word is genuinely ambiguous, state the most likely biblical sense and briefly explain the alternative.

#### Biblical Significance
Explain what this contextual meaning reveals or teaches, while staying within the evidence provided.

#### Summary
Restate the definition in one or two clear sentences.
