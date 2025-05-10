from typing import Tuple

from pydantic import BaseModel, Field

from app.core.entities.exercise import Exercise
from app.core.enums import ExerciseTopic, LanguageLevel
from app.core.value_objects.answer import ChooseAccentAnswer
from app.llm.interfaces.exercise_generator import ExerciseGenerator
from app.llm.llm_base import BaseLLMService
from app.llm.quality_assessor import ExerciseForAssessor


class ChooseAccentExerciseDataParsed(BaseModel):
    correct_accent: str = Field(description='Correct accent in this word.\n')
    incorrect_accents: list[str] = Field(
        description='Two common misspellings accents in this word.'
    )


class ChooseAccentGenerator(ExerciseGenerator):
    def __init__(self, llm_service: BaseLLMService):
        self.llm_service = llm_service

    async def generate(
        self,
        user_language: str,
        user_language_code: str,
        target_language: str,
        language_level: LanguageLevel,
        topic: ExerciseTopic,
    ) -> Tuple[Exercise, ChooseAccentAnswer, ExerciseForAssessor]:
        # TODO: LLM не умеют в ударение, сейчас не используется,
        #  но можно попробовать допилить
        raise NotImplementedError

        # parser = PydanticOutputParser(
        #     pydantic_object=ChooseAccentExerciseDataParsed
        # )
        #
        # prompt_template = (
        #     'You are helping a {user_language}-speaking learner '
        #     'of the {exercise_language} language.\n'
        #     "Generate an exercise 'Choose the correct stress':\n"
        #     '- Select *only* a commonly mispronounced {exercise_language} '
        #     'word with incorrect stress placement.\n'
        #     '- Provide exactly one correct variant with stress marked '
        #     '*only* on the stressed **vowel** using UPPER vowel letter.\n'
        #     '- Provide two incorrect but plausible stress variants \n'
        #     '- Use real common mistakes made by non-native speakers.\n'
        #     'Do not place stress on consonants.\n'
        #     'Language level: {language_level}\n'
        #     'Topic: {topic}\n'
        #     '{format_instructions}'
        # )
        #
        # chain = await self.llm_service.create_llm_chain(
        #     prompt_template, parser, is_chat_prompt=False
        # )
        #
        # input_data = {
        #     'user_language': user_language,
        #     'exercise_language': target_language,
        #     'language_level': language_level.value,
        #     'topic': topic.value,
        # }
        #
        # parsed_data = await self.llm_service.run_llm_chain(
        #     chain=chain,
        #     input_data=input_data,
        # )
        #
        # accents = (
        #         [parsed_data.correct_accent]
        #         + parsed_data.incorrect_accents
        # )
        #
        # exercise = Exercise(
        #     exercise_id=None,
        #     exercise_type=ExerciseType.CHOOSE_ACCENT,
        #     exercise_language=target_language,
        #     language_level=language_level,
        #     topic=topic,
        #     exercise_text=get_text(
        #         ExerciseType.CHOOSE_ACCENT, user_language),
        #     data=ChooseAccentExerciseData(
        #         options=accents,
        #     ),
        # )
        # correct_answer = ChooseAccentAnswer(
        #     answer=parsed_data.correct_accent)
        #
        # exercise_for_quality_assessor = ExerciseForAssessor(
        #     text=exercise.exercise_text,
        #     options=accents,
        #     correct_answer=parsed_data.correct_accent,
        #     exercise_type=ExerciseType.CHOOSE_SENTENCE,
        #     language_level=language_level,
        # )
        #
        # return exercise, correct_answer, exercise_for_quality_assessor
