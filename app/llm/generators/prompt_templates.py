BASE_SYSTEM_PROMPT_FOR_GENERATION = (
    'You are a language learning expert creating exercises '
    'for a {user_language}-speaking learner '
    'of the {exercise_language} language at the {language_level} '
    'level, focusing on the topic: {topic}.\n\n'
    'If a persona is described below, the generated exercise scenario AND '
    'the phrasing of the exercise text itself should strongly reflect their '
    'role, emotion, motivation, and communication style. '
    "The text should sound as if it's coming from this persona's "
    'perspective or is directly about a situation involving them. '
    'For example, an "Arrogant Client" might use more demanding or critical'
    ' language in the sentences, while an "Embarrassed Tourist" might use'
    ' more hesitant or apologetic phrasing.\n'
    '{persona_instructions}\n\n'
    'Follow the instructions carefully to generate a high-quality exercise.\n'
    'Ensure all generated text, including correct answers '
    'and incorrect options, uses *only* characters '
    'from the {exercise_language} alphabet. Do not use visually similar '
    'characters from other alphabets '
    "(e.g., Latin 'o' instead of Cyrillic 'о' in a Cyrillic language "
    'exercise, or vice-versa if generating for Latin-based languages).\n'
    '\n{specific_exercise_generation_instructions}\n\n'
    'Output format instructions: {format_instructions}'
)

FILL_IN_THE_BLANK_GENERATION_INSTRUCTIONS = (
    "Your task is to generate a 'fill-in-the-blank' exercise.\n"
    'Remember to consider the persona if provided: {persona_instructions}. '
    'The sentence you create should reflect this persona.\n'
    'Follow these steps using a Chain of Thought approach:\n'
    '1.  **Sentence Conception:** Create a grammatically correct and natural '
    'sentence in {exercise_language} that is appropriate for the '
    '{language_level} and {topic}. The sentence should be clear '
    'and unambiguous. '
    'The sentence should be interesting and not overly simplistic.\n'
    '2.  **Blank Selection:** Identify 1 or 2 key words in the sentence '
    "to replace with blanks (represented by '___'). **Preferably, these "
    'should be single words.** These words should be '
    'important for understanding, represent a common grammatical point, '
    'or be relevant vocabulary for the topic and level. '
    'The words chosen for blanks should ideally not be easily guessable '
    'without understanding the context or grammar.\n'
    '3.  **Correct Words:** List the exact word(s) that correctly fill '
    'the blank(s), in order. **Each word in this list must be a single '
    'word without spaces.** These are the `correct_words`.\n'
    '4.  **Incorrect Options (Distractors) Generation:** For each blank, '
    'generate 2-4 incorrect but plausible-sounding options. **Each of these '
    'options must be a single word without spaces.** These options, '
    'when inserted into the blank, *must* result in a sentence that is:\n'
    'a.  Grammatically incorrect (e.g., wrong case, tense, agreement, '
    'spelling within {exercise_language} standards).\n'
    'b.  Semantically absurd or nonsensical in the context of the sentence.\n'
    'c.  Clearly and unambiguously wrong for a native speaker or an advanced '
    'learner focusing on correctness.\n'
    '    *Crucially, an incorrect option should NOT simply change the '
    'meaning of the sentence to another valid, sensible sentence in '
    '{exercise_language}. The goal is to test specific knowledge, not to '
    'allow for alternative correct sentences via distractors.*\n'
    '    These incorrect options will form the `incorrect_options` list. '
    'Ensure these options also only use {exercise_language} alphabet '
    'characters.\n'
    '5.  **Self-Critique and Refinement (Very Important):\n'
    '    -   Review the generated `sentence_with_blanks`, the '
    '`correct_words`, and the `incorrect_options`.\n'
    '    -   **Test with Incorrect Options:** Imagine filling the blanks '
    'with each of the `incorrect_options`. '
    '        If any incorrect option results in a sentence that is still '
    "grammatically correct and makes reasonable sense (even if it's a "
    'different meaning than intended with the correct words), then the '
    'exercise is not suitable. '
    '        In this case, you *must* go back to Step 1 (new sentence) '
    'or Step 2 (different blanks/words) and try again. '
    '        The exercise fails if incorrect options lead to valid '
    'alternative sentences rather than clear errors or absurdity.\n'
    '    -   **Alphabet Check:** Double-check that all words (correct and '
    'incorrect options) use *only* characters from the {exercise_language} '
    'alphabet. '
    '        For example, if {exercise_language} is Russian or Bulgarian, '
    "do not use Latin 'a', 'o', 'c', 'p', 'x', etc., instead "
    "of Cyrillic 'а', 'о', 'с', 'р', 'х'. "
    "        If {exercise_language} is English, do not use Cyrillic 'а' "
    "for 'a'.\n"
    '6.  **Final Output:** Provide the `sentence_with_blanks`, '
    '`correct_words` (list of strings for the blanks),'
    ' and `incorrect_options` '
    '(list of strings that are definitively wrong distractors).'
)

CHOOSE_SENTENCE_GENERATION_INSTRUCTIONS = (
    "Your task is to generate a 'choose the correct sentence' exercise.\n"
    'Remember to consider the persona if provided: {persona_instructions}. '
    'The sentence you create should reflect this persona.\n'
    'Follow these steps using a Chain of Thought approach:\n'
    '1.  **Correct Sentence Conception:** Create a grammatically correct, '
    'natural, and unambiguous sentence in {exercise_language}. '
    '    This sentence should be appropriate for the {language_level} '
    'and {topic}. '
    '    It should be interesting and not overly simplistic. This will be '
    'the `correct_sentence`.\n'
    '2.  **Incorrect Sentences (Distractors) Generation:** Create 2 '
    'distinct incorrect sentences. '
    '    Each incorrect sentence must:\n'
    '    a.  Be very similar in structure and vocabulary to the '
    '`correct_sentence`.\n'
    '    b.  Contain a single, clear, and common grammatical error '
    'relevant to the {language_level} '
    '        (e.g., wrong verb tense, incorrect noun case, wrong preposition, '
    'incorrect word order if it leads to a clear error, '
    "        subject-verb agreement error, incorrect article usage if it's a "
    'definitive error, common spelling mistake based on {exercise_language} '
    'rules).\n'
    '    c.  The error should make the sentence unambiguously incorrect '
    'for a native speaker or an advanced learner focusing on correctness.\n'
    '    d.  An incorrect sentence should NOT be just a semantically '
    'different but still grammatically correct sentence. '
    '        It must contain a grammatical or structural flaw.\n'
    '    e.  Ensure these incorrect sentences also only use '
    '{exercise_language} alphabet characters.\n'
    '    These will be part of the `options` list.\n'
    '3.  **Self-Critique and Refinement (Very Important):\n'
    '    -   Review the `correct_sentence` and the two '
    '`incorrect_sentences`.\n'
    '    -   **Plausibility of Incorrect Options:** Are the incorrect '
    'options plausible distractors? Do they target common errors?\n'
    '    -   **Clarity of Errors:** Is the error in each incorrect '
    'sentence clear and unambiguous? '
    '        Could an incorrect sentence be misinterpreted as correct or '
    'merely stylistically different?\n'
    '    -   **Uniqueness of Correct Sentence:** Is the `correct_sentence` '
    'clearly the *only* correct one among the three options? '
    "        If one of the 'incorrect' sentences is actually also correct "
    'or only very subtly awkward, the exercise is not suitable. '
    '        In this case, you *must* go back to Step 1 '
    '(new correct sentence) or Step 2 (new incorrect sentences with clearer '
    'errors) and try again.\n'
    '    -   **Alphabet Check:** Double-check that all sentences '
    '(correct and incorrect) use *only* characters from the '
    '{exercise_language} alphabet. '
    '        For example, if {exercise_language} is Russian or Bulgarian, do '
    "not use Latin 'a', 'o', 'c', 'p', 'x', etc., instead "
    "of Cyrillic 'а', 'о', 'с', 'р', 'х'.\n"
    '4.  **Final Output:** Provide the `correct_sentence` and '
    'a list of two `incorrect_sentences`.'
)

STORY_COMPREHENSION_GENERATION_INSTRUCTIONS = (
    "Your task is to generate a 'Story Comprehension' exercise.\n"
    'Follow these steps:\n'
    '\n'
    '1. **Story Generation:**\n'
    '   - Create a short, coherent story (3–5 sentences) in '
    '{exercise_language}.\n'
    '   - The story should be appropriate for the {language_level} '
    'and the topic: {topic}.\n'
    '   - Use natural, grammatically correct language suitable for '
    'a learner.\n'
    '   - Include multiple details, actions, and characters to create '
    'rich content for comprehension testing.\n'
    '\n'
    '2. **Statements Generation:**\n'
    '   - Based on the story, generate three distinct statements:\n'
    '     a. `correct_statement`: a statement that accurately reflects '
    'ONE specific detail from the story (not a summary).\n'
    '        - Focus on a single, clear fact from the story\n'
    '        - Avoid overly comprehensive statements that mention '
    'multiple story elements\n'
    '        - Make it specific but not trivial\n'
    '\n'
    '     b. `incorrect_statements` (2 items): false statements that '
    'require careful reading to identify as wrong.\n'
    '        - **CRITICAL: Avoid simple negations or direct opposites**\n'
    '        - **DO NOT use patterns like "X instead of Y" or '
    '"not Y, but X"**\n'
    '        - Create statements that could be plausible if the reader '
    'misremembered or skimmed the story\n'
    '\n'
    '3. **Strategies for High-Quality Incorrect Statements:**\n'
    '   - **Subtle detail changes**: Change specific but non-obvious details '
    '(time of day, weather, emotions, reasons)\n'
    '   - **Logical extensions**: Add reasonable but unstated consequences '
    'or motivations\n'
    '   - **Context mixing**: Combine elements that exist separately in '
    'the story\n'
    '   - **Reasonable assumptions**: State logical but unconfirmed details\n'
    '\n'
    '4. **What to AVOID in Incorrect Statements:**\n'
    '   - Direct contradictions using "not...but" or "instead of" patterns\n'
    '   - Obviously absurd or completely unrelated content\n'
    '   - Simple negations of story facts\n'
    '   - Statements that any casual reader would immediately spot as wrong\n'
    '\n'
    '5. **Quality Check:**\n'
    '   - Each incorrect statement should require the reader to recall '
    'specific story details to identify as false\n'
    '   - A person who only half-remembered the story might believe '
    'the incorrect statements\n'
    '   - The correct statement should test comprehension of a key '
    'story element without being too broad\n'
    '\n'
    'The goal is to create a genuine comprehension challenge that rewards '
    'careful reading and attention to detail.'
)

STORY_COMPREHENSION_WITH_PERSONA_GENERATION_INSTRUCTIONS = (
    "Your task is to generate a 'Story Comprehension' exercise.\n"
    'You are provided with a specific persona. **The story MUST be written '
    "from the first-person perspective of this persona ('I', 'me', 'my') "
    'OR be a narrative clearly centered around this persona, strongly '
    'reflecting their described traits.**\n'
    'Persona Details: {persona_instructions}\n\n'
    'Follow these steps:\n'
    '\n'
    '1. **Story Generation (Reflecting Persona):**\n'
    '   - Create a short, coherent story (3–5 sentences) '
    'in {exercise_language}.\n'
    '   - The story must embody the persona provided: their role, emotion, '
    'motivation, and communication style should be evident in the narrative, '
    'thoughts, or dialogue.\n'
    '   - The story should be appropriate for the {language_level} and the '
    'topic: {topic}.\n'
    '   - Use natural, grammatically correct language suitable for a learner.'
    '\n'
    '   - Include multiple details, actions, and characters (if appropriate '
    'for the persona) to create rich content for comprehension testing.\n'
    '\n'
    '2. **Statements Generation:**\n'
    '   - Based on the story, generate three distinct statements:\n'
    '     a. `correct_statement`: a statement that accurately reflects '
    'ONE specific detail from the story (not a summary).\n'
    '        - Focus on a single, clear fact from the story\n'
    '        - Avoid overly comprehensive statements that mention '
    'multiple story elements\n'
    '        - Make it specific but not trivial\n'
    '\n'
    '     b. `incorrect_statements` (2 items): false statements that '
    'require careful reading to identify as wrong.\n'
    '        - **CRITICAL: Avoid simple negations or direct opposites**\n'
    '        - **DO NOT use patterns like "X instead of Y" or '
    '"not Y, but X"**\n'
    '        - Create statements that could be plausible if the reader '
    'misremembered or skimmed the story\n'
    '\n'
    '3. **Strategies for High-Quality Incorrect Statements:**\n'
    '   - **Subtle detail changes**: Change specific but non-obvious details '
    '(time of day, weather, emotions, reasons)\n'
    '   - **Logical extensions**: Add reasonable but unstated consequences '
    'or motivations\n'
    '   - **Context mixing**: Combine elements that exist separately in '
    'the story\n'
    '   - **Reasonable assumptions**: State logical but unconfirmed details\n'
    '\n'
    '4. **What to AVOID in Incorrect Statements:**\n'
    '   - Direct contradictions using "not...but" or "instead of" patterns\n'
    '   - Obviously absurd or completely unrelated content\n'
    '   - Simple negations of story facts\n'
    '   - Statements that any casual reader would immediately spot as wrong\n'
    '\n'
    '5. **Quality Check:**\n'
    '   - Each incorrect statement should require the reader to recall '
    'specific story details to identify as false\n'
    '   - A person who only half-remembered the story might believe '
    'the incorrect statements\n'
    '   - The correct statement should test comprehension of a key '
    'story element without being too broad\n'
    '\n'
    'The goal is to create a genuine comprehension challenge that rewards '
    'careful reading and attention to detail.'
)
