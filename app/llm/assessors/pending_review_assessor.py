import logging
from typing import List, Optional

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.config import settings
from app.core.entities.exercise import Exercise
from app.core.enums import ExerciseType
from app.core.value_objects.answer import Answer
from app.core.value_objects.exercise import ChooseAccentExerciseData
from app.llm.llm_base import BaseLLMService

logger = logging.getLogger(__name__)


class UserProvidedAnswerSummary(BaseModel):
    answer: Answer
    count: int
    existing_feedback: Optional[str] = None


class PendingExerciseAnalysis(BaseModel):
    is_exercise_flawed: bool = Field(
        description='True if the exercise itself or its '
        'correct answer is flawed.',
    )
    is_complex_but_correct: bool = Field(
        description='True if the exercise is correct but '
        'genuinely difficult for the level.',
    )
    primary_reason_for_user_errors: str = Field(
        description='Brief explanation of why users are '
        'likely making mistakes.',
    )
    suggested_action: str = Field(
        description="e.g., 'ARCHIVE', 'KEEP_AS_IS_COMPLEX', "
        "'REVISE_TEXT', 'REVISE_CORRECT_ANSWER', "
        "'ADD_CORRECT_ANSWER_AND_ADMIN_REVIEW', "
        "'PUBLISH_OK'",
    )
    suggested_revision: Optional[str] = Field(
        None,
        description='If revision is suggested, provide '
        'the new text/answer or the alternative correct answer.',
    )


class ChooseAccentWordAnalysis(BaseModel):
    word_to_assess: str = Field(
        description='The word from the CHOOSE_ACCENT exercise.',
    )
    is_common_and_known: bool = Field(
        description='True if the word is commonly used and widely known '
        'for the specified language and level.',
    )
    reasoning: str = Field(
        description='Brief explanation for the decision on commonness '
        'and knownness.',
    )
    confidence_level: str = Field(
        description="Confidence in the assessment: 'HIGH', 'MEDIUM', 'LOW'.",
    )


class PendingReviewAssessor(BaseLLMService):
    def __init__(
        self,
        openai_api_key: str = settings.openai_api_key,
        model_name: str = settings.openai_assessor_model_name,
    ):
        super().__init__(openai_api_key=openai_api_key, model_name=model_name)

    async def _assess_choose_accent_exercise(
        self,
        exercise: Exercise,
        user_language: str,
    ) -> PendingExerciseAnalysis:
        """
        Specialized assessment for CHOOSE_ACCENT exercises.
        Focuses on word commonness and knownness.
        """
        parser = PydanticOutputParser(pydantic_object=ChooseAccentWordAnalysis)

        if (
            isinstance(exercise.data, ChooseAccentExerciseData)
            and exercise.data.options
            and isinstance(exercise.data.options, list)
            and exercise.data.options[0]
        ):
            word_to_assess = (
                exercise.data.options[0]
                .replace(
                    '`',
                    '',
                )
                .replace("'", '')
            )
        else:
            raise ValueError('Invalid CHOOSE_ACCENT exercise data.')

        system_prompt_choose_accent = (
            'You are an AI language expert. Your task is to assess a word '
            "from a 'CHOOSE_ACCENT' "
            'exercise in {exercise_language} for a {user_language}-speaking '
            'learner at the {language_level} level, topic: {topic}.\n'
            'Focus ONLY on how common and widely known the word itself is. '
            'Do NOT assess the correctness of accent marking.\n'
            'Provide your confidence level in this assessment '
            "('HIGH', 'MEDIUM', 'LOW')."
        )

        user_prompt_template_choose_accent = (
            'Word to assess: {word_to_assess}\n\n'
            'Based on your knowledge of {exercise_language} and typical '
            'vocabulary for {language_level} learners:\n'
            '1. Is this word commonly used and widely known?\n'
            '2. Provide a brief reasoning for your decision.\n'
            '3. What is your confidence level in this assessment '
            '(HIGH, MEDIUM, LOW)?\n\n'
            '{format_instructions}'
        )

        chat_prompt = ChatPromptTemplate.from_messages(
            [
                ('system', system_prompt_choose_accent),
                ('user', user_prompt_template_choose_accent),
            ],
        )
        chain = await self.create_llm_chain(
            chat_prompt,
            parser,
            is_chat_prompt=True,
        )

        request_data = {
            'user_language': user_language,
            'exercise_language': exercise.exercise_language,
            'language_level': exercise.language_level.value,
            'topic': exercise.topic.value,
            'word_to_assess': word_to_assess,
            'format_instructions': parser.get_format_instructions(),
        }

        try:
            specific_analysis: ChooseAccentWordAnalysis = (
                await self.run_llm_chain(chain, request_data)
            )
        except Exception as e:
            logger.error(
                f'Error during CHOOSE_ACCENT specific assessment '
                f"for word '{word_to_assess}': {e}",
                exc_info=True,
            )
            return PendingExerciseAnalysis(
                is_exercise_flawed=True,
                is_complex_but_correct=False,
                primary_reason_for_user_errors=(
                    f'LLM assessment failed for CHOOSE_ACCENT word: '
                    f'{word_to_assess}. Error: {e}'
                ),
                suggested_action='ARCHIVE',
                suggested_revision=None,
            )

        if specific_analysis.is_common_and_known:
            if specific_analysis.confidence_level == 'HIGH':
                return PendingExerciseAnalysis(
                    is_exercise_flawed=False,
                    is_complex_but_correct=False,
                    primary_reason_for_user_errors=(
                        f"Word '{specific_analysis.word_to_assess}' "
                        f'is common. '
                        f'User errors likely due to accent difficulty.'
                    ),
                    suggested_action='PUBLISH_OK',
                    suggested_revision=None,
                )
            else:
                reason_for_user_errors = (
                    f"Word '{specific_analysis.word_to_assess}' might be "
                    f'common, but confidence is '
                    f'{specific_analysis.confidence_level}. '
                    f'Reasoning: {specific_analysis.reasoning}'
                )
                return PendingExerciseAnalysis(
                    is_exercise_flawed=False,
                    is_complex_but_correct=False,
                    primary_reason_for_user_errors=reason_for_user_errors,
                    suggested_action='PENDING_ADMIN_REVIEW',
                    suggested_revision=(
                        f'Verify commonness of word: '
                        f"'{specific_analysis.word_to_assess}' "
                        f'for level {exercise.language_level.value}. '
                        f'LLM confidence: '
                        f'{specific_analysis.confidence_level}.'
                    ),
                )
        else:  # Not common and known
            return PendingExerciseAnalysis(
                is_exercise_flawed=True,
                is_complex_but_correct=False,
                primary_reason_for_user_errors=(
                    f"Word '{specific_analysis.word_to_assess}' assessed as "
                    f'not common/known enough for level '
                    f'{exercise.language_level.value}. '
                    f'Reasoning: {specific_analysis.reasoning}'
                ),
                suggested_action='ARCHIVE',
                suggested_revision=None,
            )

    async def assess_pending_exercise(
        self,
        exercise: Exercise,
        correct_answers_summary: List[UserProvidedAnswerSummary],
        user_incorrect_answers_summary: List[UserProvidedAnswerSummary],
        user_language: str,
    ) -> PendingExerciseAnalysis:
        if exercise.exercise_type == ExerciseType.CHOOSE_ACCENT:
            return await self._assess_choose_accent_exercise(
                exercise,
                user_language,
            )

        parser = PydanticOutputParser(pydantic_object=PendingExerciseAnalysis)

        correct_answers_details_list = []
        for ca_summary in correct_answers_summary:
            try:
                contextual_text = (
                    exercise.data.get_answered_by_user_exercise_text(
                        ca_summary.answer,
                    )
                )
                detail = (
                    f"- '{contextual_text}' "
                    f'(chosen by {ca_summary.count} users)'
                )
                correct_answers_details_list.append(detail)
            except NotImplementedError:
                detail = (
                    f"- '{ca_summary.answer.get_answer_text()}' "
                    f'(chosen by {ca_summary.count} users)'
                )
                correct_answers_details_list.append(detail)
            except ValueError:
                logger.warning(
                    f'Mismatch between Answer type and ExerciseData '
                    f'for exercise {exercise.exercise_id}. '
                    f'Falling back to ca.answer.get_answer_text() for '
                    f'correct answer: {ca_summary.answer.type}',
                )
                detail = (
                    f"- '{ca_summary.answer.get_answer_text()}' "
                    f'(chosen by {ca_summary.count} users)'
                )
                correct_answers_details_list.append(detail)

        correct_answers_str = '\n'.join(correct_answers_details_list)
        if not correct_answers_str:
            correct_answers_str = (
                'No designated correct answers provided '
                'or no users chose them.'
            )

        user_answers_details_list = []
        for ua_summary in user_incorrect_answers_summary:
            full_answer_text = (
                exercise.data.get_answered_by_user_exercise_text(
                    ua_summary.answer,
                )
            )
            detail = (
                f"- '{full_answer_text}' (given by {ua_summary.count} users)"
            )
            if ua_summary.existing_feedback:
                detail += (
                    f'\n  Existing Feedback: "{ua_summary.existing_feedback}"'
                )
            user_answers_details_list.append(detail)

        user_answers_str = '\n'.join(user_answers_details_list)
        if not user_answers_str:
            user_answers_str = (
                'No incorrect user answers provided for analysis.'
            )

        system_prompt_base = (
            'You are an AI language learning expert. Your task is to '
            'analyze a potentially problematic '
            'exercise that many users are failing. Determine if the '
            "issue lies with the exercise's quality "
            "or if it's a genuinely complex but fair challenge.\n"
            'The exercise is for a {user_language}-speaking learner '
            'of {exercise_language} at {language_level} level, '
            'topic: {topic}.\n'
            'IMPORTANT: If you have any significant doubts about '
            'the exercise quality, its clarity, the correctness of the '
            'designated answer, the existing feedback, or the appropriateness '
            'of distractors, err on the side of caution. In such cases, you '
            'should mark the exercise as flawed or suggest archiving it. '
            'Only recommend keeping an exercise as "PUBLISHED" '
            '(e.g., by suggesting action "PUBLISH_OK" or "KEEP_AS_IS_COMPLEX"'
            ' without flaws) if you are highly confident in its quality '
            'and utility, and believe user errors stem from the exercise '
            'being a fair but complex challenge.'
        )

        specific_instructions = ''

        system_prompt = system_prompt_base + specific_instructions

        user_prompt_template = (
            'Exercise Text: {exercise_text}\n\n'
            'Designated Correct Answer(s) '
            '(in full context, with user counts):\n'
            '{correct_answers_str}\n\n'
            'Incorrect Answers Provided by Users (listed by frequency, '
            'with existing feedback if any, and user counts):\n'
            '{user_answers_str}\n\n'
            'Based on this information, please analyze:\n'
            '1. Is the exercise text itself clear and unambiguous?\n'
            '2. Is the designated correct answer(s) truly '
            'and uniquely correct? Consider how often '
            'it was chosen by users.\n'
            '3. Are the incorrect user answers due to common learner '
            'mistakes, or do they indicate a flaw in the exercise '
            '(e.g., misleading question, '
            "incorrect 'correct' answer, ambiguous options if any)?\n"
            '   Specifically, if the primary difficulty for users in '
            '{exercise_language} seems to stem from the definite/indefinite '
            'form of nouns, which can sometimes be ambiguous or have subtle '
            'rules, evaluate if any of the user-provided incorrect answers '
            'might be considered acceptable or even correct due '
            'to this nuance. '
            "If such an ambiguity exists and a user's answer "
            'is plausibly correct: '
            '   a) Your `suggested_action` could be '
            "'ADD_CORRECT_ANSWER_AND_ADMIN_REVIEW'. "
            "   b) In `suggested_revision`, specify the user's answer that "
            'should be considered as an additional correct answer. '
            '   c) If the ambiguity makes the exercise too problematic to '
            'easily fix or inherently confusing, '
            "      then `suggested_action` should be 'ARCHIVE'.\n"
            '4. If there is `Existing Feedback` provided for any incorrect '
            'user answer, is this feedback accurate, helpful, and '
            'grammatically correct in {user_language}? '
            'If the feedback is flawed, this also constitutes a flaw '
            'in the exercise handling.\n'
            '5. If the exercise is flawed (considering all aspects including '
            'text, answers, and existing feedback), what '
            'is the specific flaw?\n'
            "6. If it's complex but correct (and feedback is also correct), "
            'why might users be '
            'struggling? Consider the distribution of answers.\n\n'
            'Remember the general instruction: if in ANY doubt about the '
            'quality or correctness (including feedback), '
            'prefer to mark as flawed or suggest archiving. Return to '
            'PUBLISHED only with high confidence.\n'
            'Possible `suggested_action` values include: "PUBLISH_OK", '
            '"KEEP_AS_IS_COMPLEX", "ARCHIVE", '
            '"REVISE_TEXT", "REVISE_CORRECT_ANSWER", '
            '"ADD_CORRECT_ANSWER_AND_ADMIN_REVIEW", "REVISE_FEEDBACK".\n'
            'Provide your analysis according to the requested format.\n'
            '{format_instructions}'
        )

        chat_prompt = ChatPromptTemplate.from_messages(
            [
                ('system', system_prompt),
                ('user', user_prompt_template),
            ],
        )
        chain = await self.create_llm_chain(
            chat_prompt,
            parser,
            is_chat_prompt=True,
        )

        request_data = {
            'user_language': user_language,
            'exercise_language': exercise.exercise_language,
            'language_level': exercise.language_level.value,
            'topic': exercise.topic.value,
            'exercise_text': exercise.exercise_text,
            'correct_answers_str': correct_answers_str,
            'user_answers_str': user_answers_str,
            'format_instructions': parser.get_format_instructions(),
        }
        analysis: PendingExerciseAnalysis = await self.run_llm_chain(
            chain,
            request_data,
        )
        return analysis
