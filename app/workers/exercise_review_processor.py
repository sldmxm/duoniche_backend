import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel

from app.core.entities.exercise import Exercise as ExerciseEntity
from app.core.entities.exercise_answer import (
    ExerciseAnswer as ExerciseAnswerEntity,
)
from app.core.enums import ExerciseStatus
from app.db.db import async_session_maker
from app.db.repositories.exercise import SQLAlchemyExerciseRepository
from app.db.repositories.exercise_answers import (
    SQLAlchemyExerciseAnswerRepository,
)
from app.llm.assessors.pending_review_assessor import (
    PendingReviewAssessor,
    UserProvidedAnswerSummary,
)

logger = logging.getLogger(__name__)

EXERCISE_REVIEW_INTERVAL_SECONDS = 3 * 60 * 60
MAX_EXERCISES_TO_REVIEW_PER_CYCLE = 10


class ReviewDecision(BaseModel):
    exercise_id: int
    new_status: ExerciseStatus
    reason: str | None


async def exercise_review_processor(
    assessor: PendingReviewAssessor, stop_event: asyncio.Event
) -> List[ReviewDecision]:
    processed_decisions: List[ReviewDecision] = []
    try:
        async with async_session_maker() as session:
            exercise_repo = SQLAlchemyExerciseRepository(session)
            answer_repo = SQLAlchemyExerciseAnswerRepository(session)

            exercises_to_review: List[
                ExerciseEntity
            ] = await exercise_repo.get_exercises_by_status(
                ExerciseStatus.PENDING_REVIEW,
                limit=MAX_EXERCISES_TO_REVIEW_PER_CYCLE,
            )

            if not exercises_to_review:
                logger.info(
                    'Exercise Review Processor: '
                    'No exercises in PENDING_REVIEW.'
                )
            else:
                logger.info(
                    f'Exercise Review Processor: Found '
                    f'{len(exercises_to_review)} exercises to review.'
                )

            for exercise in exercises_to_review:
                if stop_event.is_set():
                    break
                if exercise.exercise_id is None:
                    logger.warning(f'Skipping exercise without ID: {exercise}')
                    continue

                logger.info(f'Reviewing exercise ID: {exercise.exercise_id}')

                answers_with_individual_counts: List[
                    tuple[ExerciseAnswerEntity, int]
                ] = await answer_repo.get_answers_with_attempt_counts(
                    exercise.exercise_id
                )

                if not answers_with_individual_counts:
                    logger.warning(
                        f'No ExerciseAnswers (with counts) '
                        f'found for exercise ID: '
                        f'{exercise.exercise_id}. Archiving.'
                    )
                    processed_decisions.append(
                        ReviewDecision(
                            exercise_id=exercise.exercise_id,
                            new_status=ExerciseStatus.ARCHIVED,
                            reason='No ExerciseAnswers (with counts) found.',
                        )
                    )
                    await exercise_repo.update_exercise_status_and_data(
                        exercise_id=exercise.exercise_id,
                        new_status=ExerciseStatus.ARCHIVED,
                    )
                    continue

                aggregated_answers_map: Dict[
                    tuple[str, bool], tuple[List[ExerciseAnswerEntity], int]
                ] = {}

                for ea_entity, count in answers_with_individual_counts:
                    answer_text_for_key = ea_entity.answer.get_answer_text()
                    logical_key = (answer_text_for_key, ea_entity.is_correct)

                    if logical_key not in aggregated_answers_map:
                        aggregated_answers_map[logical_key] = (
                            [ea_entity],
                            count,
                        )
                    else:
                        current_variants, current_total_count = (
                            aggregated_answers_map[logical_key]
                        )
                        current_variants.append(ea_entity)
                        aggregated_answers_map[logical_key] = (
                            current_variants,
                            current_total_count + count,
                        )

                correct_answers_summary: List[UserProvidedAnswerSummary] = []
                user_incorrect_answers_summary: List[
                    UserProvidedAnswerSummary
                ] = []

                user_language_for_assessor = 'en'

                for (_, is_correct_flag), (
                    variants,
                    total_count,
                ) in aggregated_answers_map.items():
                    representative_ea: Optional[ExerciseAnswerEntity] = None
                    if variants:
                        for v_ea in variants:
                            if (
                                v_ea.feedback_language
                                == user_language_for_assessor
                            ):
                                representative_ea = v_ea
                                break
                        if not representative_ea:
                            representative_ea = variants[0]

                    if not representative_ea:
                        raise ValueError(
                            'No representative ExerciseAnswer found'
                        )

                    feedback_to_use = (
                        representative_ea.feedback
                        if representative_ea
                        else None
                    )
                    answer_object_to_use = representative_ea.answer

                    summary_item = UserProvidedAnswerSummary(
                        answer=answer_object_to_use,
                        count=total_count,
                        existing_feedback=feedback_to_use,
                    )

                    if is_correct_flag:
                        correct_answers_summary.append(summary_item)
                    else:
                        user_incorrect_answers_summary.append(summary_item)

                has_at_least_one_correct_ref = bool(correct_answers_summary)

                if not has_at_least_one_correct_ref:
                    logger.warning(
                        f'No CORRECT reference ExerciseAnswers '
                        f'found for exercise ID: '
                        f'{exercise.exercise_id}. Archiving.'
                    )
                    processed_decisions.append(
                        ReviewDecision(
                            exercise_id=exercise.exercise_id,
                            new_status=ExerciseStatus.ARCHIVED,
                            reason='No correct reference answers found '
                            'in ExerciseAnswers (with counts).',
                        )
                    )
                    await exercise_repo.update_exercise_status_and_data(
                        exercise_id=exercise.exercise_id,
                        new_status=ExerciseStatus.ARCHIVED,
                    )
                    continue

                user_incorrect_answers_summary.sort(
                    key=lambda x: x.count, reverse=True
                )

                try:
                    analysis = await assessor.assess_pending_exercise(
                        exercise=exercise,
                        correct_answers_summary=correct_answers_summary,
                        user_incorrect_answers_summary=user_incorrect_answers_summary,
                        user_language=user_language_for_assessor,
                    )

                    formatted_correct_answers = '\n'.join(
                        [
                            f'  - Answer: '
                            f'{summary_item.answer.get_answer_text()!r}, '
                            f'Count: {summary_item.count}, '
                            f'Feedback: {summary_item.existing_feedback!r}'
                            for summary_item in correct_answers_summary
                        ]
                    )
                    if not correct_answers_summary:
                        formatted_correct_answers = (
                            '  (No correct answers summary)'
                        )
                    formatted_incorrect_answers = '\n'.join(
                        [
                            f'  - Answer: '
                            f'{summary_item.answer.get_answer_text()!r}, '
                            f'Count: {summary_item.count}, '
                            f'Feedback: {summary_item.existing_feedback!r}'
                            for summary_item in user_incorrect_answers_summary
                        ]
                    )
                    if not user_incorrect_answers_summary:
                        formatted_incorrect_answers = (
                            '  (No incorrect answers summary)'
                        )
                    logger.info(
                        f'Assessment for exercise ID '
                        f'{exercise.exercise_id}: \n'
                        f'Exercise: '
                        f'{exercise.data.model_dump_json(indent=2)}\n'
                        f'Correct Answers Summary:\n'
                        f'{formatted_correct_answers}\n'
                        f'User Incorrect Answers Summary:\n'
                        f'{formatted_incorrect_answers}\n'
                        f'Assessment: '
                        f'{analysis.model_dump_json(indent=2)}'
                    )

                    current_comments = exercise.comments or ''
                    timestamp = datetime.now().strftime(
                        '%Y-%m-%d %H:%M:%S UTC'
                    )
                    new_status: ExerciseStatus
                    reason_for_decision: str

                    if analysis.suggested_revision:
                        new_status = ExerciseStatus.PENDING_ADMIN_REVIEW
                    elif 'PUBLISH_OK' in analysis.suggested_action.upper() or (
                        'KEEP_AS_IS_COMPLEX'
                        in analysis.suggested_action.upper()
                        and not analysis.is_exercise_flawed
                    ):
                        new_status = ExerciseStatus.PUBLISHED
                    elif (
                        analysis.is_exercise_flawed
                        or 'ARCHIVE' in analysis.suggested_action.upper()
                    ):
                        new_status = ExerciseStatus.ARCHIVED
                    elif (
                        'PENDING_ADMIN_REVIEW'
                        in analysis.suggested_action.upper()
                        and not analysis.suggested_revision
                    ):
                        new_status = ExerciseStatus.PENDING_ADMIN_REVIEW
                    else:
                        logger.info(
                            f'Exercise {exercise.exercise_id} did not meet '
                            f'clear criteria for PUBLISH or ADMIN_REVIEW, '
                            f'and was not explicitly flawed/archived '
                            f'by assessor. Defaulting to ARCHIVE. '
                            f'Assessor action: {analysis.suggested_action}, '
                            f'Flawed: {analysis.is_exercise_flawed}, '
                            f'Complex: {analysis.is_complex_but_correct}'
                        )
                        new_status = ExerciseStatus.ARCHIVED

                    if new_status == ExerciseStatus.PENDING_ADMIN_REVIEW:
                        if analysis.suggested_revision:
                            reason_for_decision = (
                                f'Reason: '
                                f'{analysis.primary_reason_for_user_errors}. '
                                f'Assessor suggested revision: '
                                f"'{analysis.suggested_revision}'. "
                                f'(Action: {analysis.suggested_action}, '
                                f'Flawed: {analysis.is_exercise_flawed}). '
                                f'Status set to PENDING_ADMIN_REVIEW.'
                            )
                        else:
                            reason_for_decision = (
                                f'Reason: '
                                f'{analysis.primary_reason_for_user_errors}. '
                                f'Needs admin verification. '
                                f'(Action: {analysis.suggested_action}, '
                                f'Flawed: {analysis.is_exercise_flawed}). '
                                f'Status set to PENDING_ADMIN_REVIEW.'
                            )
                    elif new_status == ExerciseStatus.PUBLISHED:
                        if (
                            'KEEP_AS_IS_COMPLEX'
                            in analysis.suggested_action.upper()
                        ):
                            reason_for_decision = (
                                'Assessor: complex but correct.'
                                ' No revision suggested. '
                                'Status set to PUBLISHED.'
                            )
                        elif 'PUBLISH_OK' in analysis.suggested_action.upper():
                            reason_for_decision = (
                                'Assessor: exercise is OK. '
                                'Status set to PUBLISHED.'
                            )
                        else:
                            reason_for_decision = (
                                'Assessor: reviewed and approved. '
                                'Status set to PUBLISHED.'
                            )
                    elif new_status == ExerciseStatus.ARCHIVED:
                        if (
                            analysis.is_exercise_flawed
                            or 'ARCHIVE' in analysis.suggested_action.upper()
                        ):
                            reason_for_decision = (
                                f'Reason: '
                                f'{analysis.primary_reason_for_user_errors}. '
                                f'(Action: {analysis.suggested_action}, '
                                f'Flawed: {analysis.is_exercise_flawed}). '
                                f'Status set to ARCHIVED.'
                            )
                        else:
                            reason_for_decision = (
                                f'Reason: '
                                f'{analysis.primary_reason_for_user_errors}. '
                                f'Defaulted to ARCHIVE as no clear '
                                f'publish/admin_review signal. '
                                f'(Action: {analysis.suggested_action}, '
                                f'Flawed: {analysis.is_exercise_flawed}, '
                                f'Complex: {analysis.is_complex_but_correct}).'
                            )
                    else:
                        reason_for_decision = (
                            f'Unhandled status path for {new_status.value}'
                        )

                    comment_log_entry_parts = [
                        f'Review at {timestamp}',
                        f'  Assessor Conclusion: '
                        f'{analysis.primary_reason_for_user_errors}',
                        f'  Assessor Suggested Action: '
                        f'{analysis.suggested_action}',
                        f'  Is Flawed: ' f'{analysis.is_exercise_flawed}',
                        f'  Is Complex but Correct: '
                        f'{analysis.is_complex_but_correct}',
                    ]
                    if analysis.suggested_revision:
                        comment_log_entry_parts.append(
                            f'  Assessor Suggested Revision: '
                            f'{analysis.suggested_revision}'
                        )
                    comment_log_entry_parts.append(
                        f'  Processor Action: '
                        f'Status changed to {new_status.value}'
                    )

                    new_comment_entry = '\n---\n' + '\n'.join(
                        comment_log_entry_parts
                    )
                    final_comments = current_comments + new_comment_entry

                    processed_decisions.append(
                        ReviewDecision(
                            exercise_id=exercise.exercise_id,
                            new_status=new_status,
                            reason=reason_for_decision,
                        )
                    )
                    await exercise_repo.update_exercise_status_and_data(
                        exercise_id=exercise.exercise_id,
                        new_status=new_status,
                        comments=final_comments,
                    )

                except Exception as e_assess:
                    logger.error(
                        f'Error during assessment of exercise ID '
                        f'{exercise.exercise_id}: {e_assess}',
                        exc_info=True,
                    )
                    processed_decisions.append(
                        ReviewDecision(
                            exercise_id=exercise.exercise_id,
                            new_status=ExerciseStatus.PENDING_REVIEW,
                            reason=f'Assessment error: {e_assess}',
                        )
                    )
            await session.commit()
    except Exception as e:
        logger.error(
            f'Error in Exercise Review Processor cycle: {e}', exc_info=True
        )
        if 'session' in locals() and session.is_active:
            await session.rollback()

    return processed_decisions


async def exercise_review_processor_loop(stop_event: asyncio.Event):
    logger.info('Exercise Review Processor Worker started.')
    assessor = PendingReviewAssessor()

    while not stop_event.is_set():
        logger.info('Exercise Review Processor: Starting new cycle.')
        processed_decisions = await exercise_review_processor(
            stop_event=stop_event,
            assessor=assessor,
        )
        logger.info(
            f'Exercise Review Processor: Cycle finished. '
            f'Decisions: {processed_decisions}'
        )
        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=EXERCISE_REVIEW_INTERVAL_SECONDS
            )
        except asyncio.TimeoutError:
            pass
        except asyncio.CancelledError:
            logger.info(
                'Exercise Review Processor loop task cancelled '
                'during sleep interval.'
            )
            break
    logger.info('Exercise Review Processor loop terminated.')
