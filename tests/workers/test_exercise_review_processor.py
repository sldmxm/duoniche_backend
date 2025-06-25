import asyncio
import contextlib
from datetime import datetime
from unittest.mock import AsyncMock, create_autospec, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.configs.enums import (
    ExerciseStatus,
    ExerciseType,
    LanguageLevel,
)
from app.core.configs.generation.config import ExerciseTopic
from app.core.entities.exercise import Exercise as ExerciseEntity
from app.core.entities.exercise_answer import (
    ExerciseAnswer as ExerciseAnswerEntity,
)
from app.core.value_objects.answer import FillInTheBlankAnswer
from app.core.value_objects.exercise import (
    ChooseAccentExerciseData,
    FillInTheBlankExerciseData,
)
from app.db.repositories.exercise import SQLAlchemyExerciseRepository
from app.db.repositories.exercise_answers import (
    SQLAlchemyExerciseAnswerRepository,
)
from app.llm.assessors.pending_review_assessor import (
    PendingExerciseAnalysis,
    PendingReviewAssessor,
)
from app.workers.exercise_review_processor import (
    exercise_review_processor,
    exercise_review_processor_loop,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_exercise_repo():
    return create_autospec(
        SQLAlchemyExerciseRepository, instance=True, spec_set=True
    )


@pytest.fixture
def mock_answer_repo():
    return create_autospec(
        SQLAlchemyExerciseAnswerRepository, instance=True, spec_set=True
    )


@pytest.fixture
def mock_assessor():
    mock = create_autospec(PendingReviewAssessor, instance=True, spec_set=True)
    mock._assess_choose_accent_exercise = AsyncMock()
    return mock


@pytest.fixture
def sample_exercise():
    return ExerciseEntity(
        exercise_id=1,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK,
        exercise_language='en',
        language_level=LanguageLevel.A2,
        topic=ExerciseTopic.GENERAL,
        exercise_text='This is a test ____.',
        data=FillInTheBlankExerciseData(
            text_with_blanks='This is a test ____.',
            words=['answer'],
        ),
        status=ExerciseStatus.PENDING_REVIEW,
        comments=None,
    )


@pytest.fixture
def sample_correct_answer_entity():
    return ExerciseAnswerEntity(
        answer_id=101,
        exercise_id=1,
        answer=FillInTheBlankAnswer(words=['answer']),
        is_correct=True,
        feedback='Correct!',
        feedback_language='en',
        created_at=datetime.now(),
        created_by='test',
    )


@pytest.fixture
def sample_incorrect_answer_entity_en():
    return ExerciseAnswerEntity(
        answer_id=102,
        exercise_id=1,
        answer=FillInTheBlankAnswer(words=['wrong']),
        is_correct=False,
        feedback='Incorrect.',
        feedback_language='en',
        created_at=datetime.now(),
        created_by='test',
    )


@pytest.fixture
def sample_incorrect_answer_entity_ru():
    return ExerciseAnswerEntity(
        answer_id=103,
        exercise_id=1,
        answer=FillInTheBlankAnswer(words=['wrong']),
        is_correct=False,
        feedback='Неправильно.',
        feedback_language='ru',
        created_at=datetime.now(),
        created_by='test',
    )


@pytest.fixture
def sample_incorrect_answer_entity_other():
    return ExerciseAnswerEntity(
        answer_id=104,
        exercise_id=1,
        answer=FillInTheBlankAnswer(words=['another']),
        is_correct=False,
        feedback='Try again.',
        feedback_language='en',
        created_at=datetime.now(),
        created_by='test',
    )


@pytest.fixture
def sample_assessor_analysis_publish_ok():
    return PendingExerciseAnalysis(
        is_exercise_flawed=False,
        is_complex_but_correct=False,
        primary_reason_for_user_errors='Exercise is clear and correct.',
        suggested_action='PUBLISH_OK',
        suggested_revision=None,
    )


@pytest.fixture
def sample_assessor_analysis_keep_complex():
    return PendingExerciseAnalysis(
        is_exercise_flawed=False,
        is_complex_but_correct=True,
        primary_reason_for_user_errors='Exercise is complex but correct.',
        suggested_action='KEEP_AS_IS_COMPLEX',
        suggested_revision=None,
    )


@pytest.fixture
def assessor_analysis_archive_flawed():
    return PendingExerciseAnalysis(
        is_exercise_flawed=True,
        is_complex_but_correct=False,
        primary_reason_for_user_errors='Correct answer is ambiguous.',
        suggested_action='ARCHIVE',
        suggested_revision=None,
    )


@pytest.fixture
def sample_assessor_analysis_admin_review_revision():
    return PendingExerciseAnalysis(
        is_exercise_flawed=True,
        is_complex_but_correct=False,
        primary_reason_for_user_errors='Incorrect option is also correct.',
        suggested_action='ADD_CORRECT_ANSWER_AND_ADMIN_REVIEW',
        suggested_revision='Add "another" as a correct answer.',
    )


@pytest.fixture
def sample_assessor_analysis_admin_review_no_revision():
    return PendingExerciseAnalysis(
        is_exercise_flawed=False,
        is_complex_but_correct=False,
        primary_reason_for_user_errors='Word commonness uncertain.',
        suggested_action='PENDING_ADMIN_REVIEW',
        suggested_revision=None,
    )


@pytest.fixture
def assessor_analysis_default_archive():
    return PendingExerciseAnalysis(
        is_exercise_flawed=False,
        is_complex_but_correct=False,
        primary_reason_for_user_errors='Unclear reason for user errors.',
        suggested_action='NEUTRAL_ASSESSMENT',
        suggested_revision=None,
    )


@contextlib.contextmanager
def patch_processor_dependencies_manager(
    mock_exercise_repo, mock_answer_repo, mock_session_context_manager
):
    with (
        patch(
            'app.workers.exercise_review_processor.async_session_maker',
            return_value=mock_session_context_manager,
        ) as p1,
        patch(
            'app.workers.exercise_review_processor.SQLAlchemyExerciseRepository',
            return_value=mock_exercise_repo,
        ) as p2,
        patch(
            'app.workers.exercise_review_processor.SQLAlchemyExerciseAnswerRepository',
            return_value=mock_answer_repo,
        ) as p3,
    ):
        yield (p1, p2, p3)


async def test_exercise_review_processor_no_exercises(
    mock_exercise_repo: AsyncMock,
    mock_answer_repo: AsyncMock,
    mock_assessor: AsyncMock,
):
    mock_exercise_repo.get_exercises_by_status.return_value = []
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = AsyncMock(spec=AsyncSession)
    mock_session_context.__aexit__ = AsyncMock(return_value=False)

    with patch_processor_dependencies_manager(
        mock_exercise_repo, mock_answer_repo, mock_session_context
    ):
        stop_event = asyncio.Event()
        decisions = await exercise_review_processor(
            assessor=mock_assessor,
            stop_event=stop_event,
        )

    mock_exercise_repo.get_exercises_by_status.assert_awaited_once()
    mock_answer_repo.get_answers_with_attempt_counts.assert_not_awaited()
    mock_assessor.assess_pending_exercise.assert_not_awaited()
    mock_exercise_repo.update_exercise_status_and_data.assert_not_awaited()
    assert decisions == []


async def test_exercise_review_processor_no_answers(
    mock_exercise_repo: AsyncMock,
    mock_answer_repo: AsyncMock,
    mock_assessor: AsyncMock,
    sample_exercise: ExerciseEntity,
):
    mock_exercise_repo.get_exercises_by_status.return_value = [sample_exercise]
    mock_answer_repo.get_answers_with_attempt_counts.return_value = []
    mock_exercise_repo.update_exercise_status_and_data.return_value = (
        sample_exercise
    )
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = AsyncMock(spec=AsyncSession)
    mock_session_context.__aexit__ = AsyncMock(return_value=False)

    with patch_processor_dependencies_manager(
        mock_exercise_repo, mock_answer_repo, mock_session_context
    ):
        stop_event = asyncio.Event()
        decisions = await exercise_review_processor(
            assessor=mock_assessor,
            stop_event=stop_event,
        )

    mock_exercise_repo.get_exercises_by_status.assert_awaited_once()
    mock_answer_repo.get_answers_with_attempt_counts.assert_awaited_once_with(
        sample_exercise.exercise_id,
    )
    mock_assessor.assess_pending_exercise.assert_not_awaited()
    mock_exercise_repo.update_exercise_status_and_data.assert_awaited_once()
    call_args_list = (
        mock_exercise_repo.update_exercise_status_and_data.await_args_list
    )
    assert len(call_args_list) == 1
    args, kwargs = call_args_list[0]

    assert kwargs['exercise_id'] == sample_exercise.exercise_id
    assert kwargs['new_status'] == ExerciseStatus.ARCHIVED
    assert kwargs.get('comments') is None

    assert len(decisions) == 1
    assert decisions[0].exercise_id == sample_exercise.exercise_id
    assert decisions[0].new_status == ExerciseStatus.ARCHIVED
    assert decisions[0].reason == 'No ExerciseAnswers (with counts) found.'


async def test_exercise_review_processor_no_correct_answers(
    mock_exercise_repo: AsyncMock,
    mock_answer_repo: AsyncMock,
    mock_assessor: AsyncMock,
    sample_exercise: ExerciseEntity,
    sample_incorrect_answer_entity_en: ExerciseAnswerEntity,
):
    mock_exercise_repo.get_exercises_by_status.return_value = [sample_exercise]
    mock_answer_repo.get_answers_with_attempt_counts.return_value = [
        (sample_incorrect_answer_entity_en, 5)
    ]
    mock_exercise_repo.update_exercise_status_and_data.return_value = (
        sample_exercise
    )
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = AsyncMock(spec=AsyncSession)
    mock_session_context.__aexit__ = AsyncMock(return_value=False)

    with patch_processor_dependencies_manager(
        mock_exercise_repo, mock_answer_repo, mock_session_context
    ):
        stop_event = asyncio.Event()
        decisions = await exercise_review_processor(
            assessor=mock_assessor,
            stop_event=stop_event,
        )

    mock_exercise_repo.get_exercises_by_status.assert_awaited_once()
    mock_answer_repo.get_answers_with_attempt_counts.assert_awaited_once_with(
        sample_exercise.exercise_id,
    )
    mock_assessor.assess_pending_exercise.assert_not_awaited()
    mock_exercise_repo.update_exercise_status_and_data.assert_awaited_once()
    call_args_list = (
        mock_exercise_repo.update_exercise_status_and_data.await_args_list
    )
    assert len(call_args_list) == 1
    args, kwargs = call_args_list[0]

    assert kwargs['exercise_id'] == sample_exercise.exercise_id
    assert kwargs['new_status'] == ExerciseStatus.ARCHIVED
    assert kwargs.get('comments') is None

    assert len(decisions) == 1
    assert decisions[0].exercise_id == sample_exercise.exercise_id
    assert decisions[0].new_status == ExerciseStatus.ARCHIVED
    assert (
        decisions[0].reason == 'No correct reference answers found '
        'in ExerciseAnswers (with counts).'
    )


async def test_exercise_review_processor_publish_ok(
    mock_exercise_repo: AsyncMock,
    mock_answer_repo: AsyncMock,
    mock_assessor: AsyncMock,
    sample_exercise: ExerciseEntity,
    sample_correct_answer_entity: ExerciseAnswerEntity,
    sample_incorrect_answer_entity_en: ExerciseAnswerEntity,
    sample_assessor_analysis_publish_ok: PendingExerciseAnalysis,
):
    mock_exercise_repo.get_exercises_by_status.return_value = [sample_exercise]
    mock_answer_repo.get_answers_with_attempt_counts.return_value = [
        (sample_correct_answer_entity, 10),
        (sample_incorrect_answer_entity_en, 5),
    ]
    mock_assessor.assess_pending_exercise.return_value = (
        sample_assessor_analysis_publish_ok
    )
    mock_exercise_repo.update_exercise_status_and_data.return_value = (
        sample_exercise
    )
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = AsyncMock(spec=AsyncSession)
    mock_session_context.__aexit__ = AsyncMock(return_value=False)

    with patch_processor_dependencies_manager(
        mock_exercise_repo, mock_answer_repo, mock_session_context
    ):
        stop_event = asyncio.Event()
        decisions = await exercise_review_processor(
            assessor=mock_assessor,
            stop_event=stop_event,
        )

    mock_exercise_repo.get_exercises_by_status.assert_awaited_once()
    mock_answer_repo.get_answers_with_attempt_counts.assert_awaited_once_with(
        sample_exercise.exercise_id,
    )
    mock_assessor.assess_pending_exercise.assert_awaited_once()

    call_obj = mock_assessor.assess_pending_exercise.await_args_list[0]
    called_kwargs = call_obj.kwargs

    assert called_kwargs['exercise'].exercise_id == sample_exercise.exercise_id
    assert len(called_kwargs['correct_answers_summary']) == 1
    assert (
        called_kwargs['correct_answers_summary'][0].answer.get_answer_text()
        == 'answer'
    )
    assert called_kwargs['correct_answers_summary'][0].count == 10
    assert len(called_kwargs['user_incorrect_answers_summary']) == 1
    assert (
        called_kwargs['user_incorrect_answers_summary'][
            0
        ].answer.get_answer_text()
        == 'wrong'
    )
    assert called_kwargs['user_incorrect_answers_summary'][0].count == 5

    mock_exercise_repo.update_exercise_status_and_data.assert_awaited_once()

    update_call_args_list = (
        mock_exercise_repo.update_exercise_status_and_data.await_args_list
    )
    assert len(update_call_args_list) == 1
    args, kwargs = update_call_args_list[0]

    updated_exercise_id = kwargs['exercise_id']
    new_status = kwargs['new_status']
    comments = kwargs['comments']

    assert updated_exercise_id == sample_exercise.exercise_id
    assert new_status == ExerciseStatus.PUBLISHED
    assert comments is not None
    assert 'Review at' in comments
    assert 'Assessor Suggested Action: PUBLISH_OK' in comments
    assert 'Processor Action: Status changed to published' in comments

    assert len(decisions) == 1
    assert decisions[0].exercise_id == sample_exercise.exercise_id
    assert decisions[0].new_status == ExerciseStatus.PUBLISHED
    assert (
        'Assessor: exercise is OK. Status set to PUBLISHED.'
        in decisions[0].reason
    )


async def test_exercise_review_processor_keep_complex(
    mock_exercise_repo: AsyncMock,
    mock_answer_repo: AsyncMock,
    mock_assessor: AsyncMock,
    sample_exercise: ExerciseEntity,
    sample_correct_answer_entity: ExerciseAnswerEntity,
    sample_incorrect_answer_entity_en: ExerciseAnswerEntity,
    sample_assessor_analysis_keep_complex: PendingExerciseAnalysis,
):
    mock_exercise_repo.get_exercises_by_status.return_value = [sample_exercise]
    mock_answer_repo.get_answers_with_attempt_counts.return_value = [
        (sample_correct_answer_entity, 10),
        (sample_incorrect_answer_entity_en, 5),
    ]
    mock_assessor.assess_pending_exercise.return_value = (
        sample_assessor_analysis_keep_complex
    )
    mock_exercise_repo.update_exercise_status_and_data.return_value = (
        sample_exercise
    )
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = AsyncMock(spec=AsyncSession)
    mock_session_context.__aexit__ = AsyncMock(return_value=False)

    with patch_processor_dependencies_manager(
        mock_exercise_repo, mock_answer_repo, mock_session_context
    ):
        stop_event = asyncio.Event()
        decisions = await exercise_review_processor(
            assessor=mock_assessor,
            stop_event=stop_event,
        )

    mock_assessor.assess_pending_exercise.assert_awaited_once()
    mock_exercise_repo.update_exercise_status_and_data.assert_awaited_once()

    update_call_args_list = (
        mock_exercise_repo.update_exercise_status_and_data.await_args_list
    )
    assert len(update_call_args_list) == 1
    args, kwargs = update_call_args_list[0]

    updated_exercise_id = kwargs['exercise_id']
    new_status = kwargs['new_status']
    comments = kwargs['comments']

    assert updated_exercise_id == sample_exercise.exercise_id
    assert new_status == ExerciseStatus.PUBLISHED
    assert comments is not None
    assert 'Assessor Suggested Action: KEEP_AS_IS_COMPLEX' in comments
    assert 'Processor Action: Status changed to published' in comments

    assert len(decisions) == 1
    assert decisions[0].exercise_id == sample_exercise.exercise_id
    assert decisions[0].new_status == ExerciseStatus.PUBLISHED
    assert (
        'Assessor: complex but correct. No revision suggested. '
        'Status set to PUBLISHED.' in decisions[0].reason
    )


async def test_exercise_review_processor_archive_flawed(
    mock_exercise_repo: AsyncMock,
    mock_answer_repo: AsyncMock,
    mock_assessor: AsyncMock,
    sample_exercise: ExerciseEntity,
    sample_correct_answer_entity: ExerciseAnswerEntity,
    sample_incorrect_answer_entity_en: ExerciseAnswerEntity,
    assessor_analysis_archive_flawed: PendingExerciseAnalysis,
):
    mock_exercise_repo.get_exercises_by_status.return_value = [sample_exercise]
    mock_answer_repo.get_answers_with_attempt_counts.return_value = [
        (sample_correct_answer_entity, 10),
        (sample_incorrect_answer_entity_en, 5),
    ]
    mock_assessor.assess_pending_exercise.return_value = (
        assessor_analysis_archive_flawed
    )
    mock_exercise_repo.update_exercise_status_and_data.return_value = (
        sample_exercise
    )
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = AsyncMock(spec=AsyncSession)
    mock_session_context.__aexit__ = AsyncMock(return_value=False)

    with patch_processor_dependencies_manager(
        mock_exercise_repo, mock_answer_repo, mock_session_context
    ):
        stop_event = asyncio.Event()
        decisions = await exercise_review_processor(
            assessor=mock_assessor,
            stop_event=stop_event,
        )

    mock_assessor.assess_pending_exercise.assert_awaited_once()
    mock_exercise_repo.update_exercise_status_and_data.assert_awaited_once()

    update_call_args_list = (
        mock_exercise_repo.update_exercise_status_and_data.await_args_list
    )
    assert len(update_call_args_list) == 1
    args, kwargs = update_call_args_list[0]

    updated_exercise_id = kwargs['exercise_id']
    new_status = kwargs['new_status']
    comments = kwargs['comments']

    assert updated_exercise_id == sample_exercise.exercise_id
    assert new_status == ExerciseStatus.ARCHIVED
    assert comments is not None
    assert 'Assessor Suggested Action: ARCHIVE' in comments
    assert 'Is Flawed: True' in comments
    assert 'Processor Action: Status changed to archived' in comments

    assert len(decisions) == 1
    assert decisions[0].exercise_id == sample_exercise.exercise_id
    assert decisions[0].new_status == ExerciseStatus.ARCHIVED
    assert decisions[0].reason is not None
    assert decisions[0].reason == (
        f'Reason: '
        f'{assessor_analysis_archive_flawed.primary_reason_for_user_errors}. '
        f'(Action: '
        f'{assessor_analysis_archive_flawed.suggested_action}, '
        f'Flawed: '
        f'{assessor_analysis_archive_flawed.is_exercise_flawed}). '
        f'Status set to ARCHIVED.'
    )


async def test_exercise_review_processor_admin_review_revision(
    mock_exercise_repo: AsyncMock,
    mock_answer_repo: AsyncMock,
    mock_assessor: AsyncMock,
    sample_exercise: ExerciseEntity,
    sample_correct_answer_entity: ExerciseAnswerEntity,
    sample_incorrect_answer_entity_en: ExerciseAnswerEntity,
    sample_assessor_analysis_admin_review_revision: PendingExerciseAnalysis,
):
    mock_exercise_repo.get_exercises_by_status.return_value = [sample_exercise]
    mock_answer_repo.get_answers_with_attempt_counts.return_value = [
        (sample_correct_answer_entity, 10),
        (sample_incorrect_answer_entity_en, 5),
    ]
    mock_assessor.assess_pending_exercise.return_value = (
        sample_assessor_analysis_admin_review_revision
    )
    mock_exercise_repo.update_exercise_status_and_data.return_value = (
        sample_exercise
    )
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = AsyncMock(spec=AsyncSession)
    mock_session_context.__aexit__ = AsyncMock(return_value=False)

    with patch_processor_dependencies_manager(
        mock_exercise_repo, mock_answer_repo, mock_session_context
    ):
        stop_event = asyncio.Event()
        decisions = await exercise_review_processor(
            assessor=mock_assessor,
            stop_event=stop_event,
        )

    mock_assessor.assess_pending_exercise.assert_awaited_once()
    mock_exercise_repo.update_exercise_status_and_data.assert_awaited_once()

    update_call_args_list = (
        mock_exercise_repo.update_exercise_status_and_data.await_args_list
    )
    assert len(update_call_args_list) == 1
    args, kwargs = update_call_args_list[0]

    updated_exercise_id = kwargs['exercise_id']
    new_status = kwargs['new_status']
    comments = kwargs['comments']

    assert updated_exercise_id == sample_exercise.exercise_id
    assert new_status == ExerciseStatus.PENDING_ADMIN_REVIEW
    assert comments is not None
    assert (
        'Assessor Suggested Action: ADD_CORRECT_ANSWER_AND_ADMIN_REVIEW'
        in comments
    )
    assert (
        'Assessor Suggested Revision: Add "another" as a correct answer.'
        in comments
    )
    assert (
        'Processor Action: Status changed to pending_admin_review' in comments
    )

    assert len(decisions) == 1
    assert decisions[0].exercise_id == sample_exercise.exercise_id
    assert decisions[0].new_status == ExerciseStatus.PENDING_ADMIN_REVIEW
    assert (
        'Assessor suggested revision: \'Add "another" as a correct answer.\'.'
        in decisions[0].reason
    )


async def test_exercise_review_processor_admin_review_no_revision(
    mock_exercise_repo: AsyncMock,
    mock_answer_repo: AsyncMock,
    mock_assessor: AsyncMock,
    sample_exercise: ExerciseEntity,
    sample_correct_answer_entity: ExerciseAnswerEntity,
    sample_incorrect_answer_entity_en: ExerciseAnswerEntity,
    sample_assessor_analysis_admin_review_no_revision: PendingExerciseAnalysis,
):
    choose_accent_exercise = sample_exercise.model_copy(deep=True)
    choose_accent_exercise.exercise_type = ExerciseType.CHOOSE_ACCENT
    choose_accent_exercise.data = ChooseAccentExerciseData(
        options=['сло̀во', 'слово̀'],
    )

    mock_exercise_repo.get_exercises_by_status.return_value = [
        choose_accent_exercise
    ]
    mock_answer_repo.get_answers_with_attempt_counts.return_value = [
        (sample_correct_answer_entity, 10),
        (sample_incorrect_answer_entity_en, 5),
    ]
    mock_assessor.assess_pending_exercise.return_value = (
        sample_assessor_analysis_admin_review_no_revision
    )

    mock_exercise_repo.update_exercise_status_and_data.return_value = (
        choose_accent_exercise
    )
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = AsyncMock(spec=AsyncSession)
    mock_session_context.__aexit__ = AsyncMock(return_value=False)

    with patch_processor_dependencies_manager(
        mock_exercise_repo, mock_answer_repo, mock_session_context
    ):
        stop_event = asyncio.Event()
        decisions = await exercise_review_processor(
            assessor=mock_assessor,
            stop_event=stop_event,
        )

    mock_exercise_repo.get_exercises_by_status.assert_awaited_once()
    mock_answer_repo.get_answers_with_attempt_counts.assert_awaited_once_with(
        choose_accent_exercise.exercise_id,
    )
    mock_assessor.assess_pending_exercise.assert_awaited_once()

    mock_exercise_repo.update_exercise_status_and_data.assert_awaited_once()
    update_call_args_list = (
        mock_exercise_repo.update_exercise_status_and_data.await_args_list
    )
    assert len(update_call_args_list) == 1
    args, kwargs = update_call_args_list[0]

    updated_exercise_id = kwargs['exercise_id']
    new_status = kwargs['new_status']
    comments = kwargs['comments']

    assert updated_exercise_id == choose_accent_exercise.exercise_id
    assert new_status == ExerciseStatus.PENDING_ADMIN_REVIEW
    assert comments is not None
    assert 'Assessor Suggested Action: PENDING_ADMIN_REVIEW' in comments
    assert 'Assessor Suggested Revision: None' not in comments
    assert (
        'Processor Action: Status changed to pending_admin_review' in comments
    )

    assert len(decisions) == 1
    assert decisions[0].exercise_id == choose_accent_exercise.exercise_id
    assert decisions[0].new_status == ExerciseStatus.PENDING_ADMIN_REVIEW
    assert 'Needs admin verification.' in decisions[0].reason


async def test_exercise_review_processor_default_archive(
    mock_exercise_repo: AsyncMock,
    mock_answer_repo: AsyncMock,
    mock_assessor: AsyncMock,
    sample_exercise: ExerciseEntity,
    sample_correct_answer_entity: ExerciseAnswerEntity,
    sample_incorrect_answer_entity_en: ExerciseAnswerEntity,
    assessor_analysis_default_archive: PendingExerciseAnalysis,
):
    mock_exercise_repo.get_exercises_by_status.return_value = [sample_exercise]
    mock_answer_repo.get_answers_with_attempt_counts.return_value = [
        (sample_correct_answer_entity, 10),
        (sample_incorrect_answer_entity_en, 5),
    ]
    mock_assessor.assess_pending_exercise.return_value = (
        assessor_analysis_default_archive
    )
    mock_exercise_repo.update_exercise_status_and_data.return_value = (
        sample_exercise
    )
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = AsyncMock(spec=AsyncSession)
    mock_session_context.__aexit__ = AsyncMock(return_value=False)

    with patch_processor_dependencies_manager(
        mock_exercise_repo, mock_answer_repo, mock_session_context
    ):
        stop_event = asyncio.Event()
        decisions = await exercise_review_processor(
            assessor=mock_assessor,
            stop_event=stop_event,
        )

    mock_assessor.assess_pending_exercise.assert_awaited_once()
    mock_exercise_repo.update_exercise_status_and_data.assert_awaited_once()

    update_call_args_list = (
        mock_exercise_repo.update_exercise_status_and_data.await_args_list
    )
    assert len(update_call_args_list) == 1
    args, kwargs = update_call_args_list[0]

    updated_exercise_id = kwargs['exercise_id']
    new_status = kwargs['new_status']
    comments = kwargs['comments']

    assert updated_exercise_id == sample_exercise.exercise_id
    assert new_status == ExerciseStatus.ARCHIVED
    assert comments is not None
    assert 'Assessor Suggested Action: NEUTRAL_ASSESSMENT' in comments
    assert 'Processor Action: Status changed to archived' in comments

    assert len(decisions) == 1
    assert decisions[0].exercise_id == sample_exercise.exercise_id
    assert decisions[0].new_status == ExerciseStatus.ARCHIVED
    assert decisions[0].reason is not None
    assert decisions[0].reason == (
        f'Reason: '
        f'{assessor_analysis_default_archive.primary_reason_for_user_errors}. '
        f'Defaulted to ARCHIVE as no clear publish/admin_review signal. '
        f'(Action: '
        f'{assessor_analysis_default_archive.suggested_action}, '
        f'Flawed: '
        f'{assessor_analysis_default_archive.is_exercise_flawed}, '
        f'Complex: '
        f'{assessor_analysis_default_archive.is_complex_but_correct}).'
    )


async def test_exercise_review_processor_aggregates_answers(
    mock_exercise_repo: AsyncMock,
    mock_answer_repo: AsyncMock,
    mock_assessor: AsyncMock,
    sample_exercise: ExerciseEntity,
    sample_correct_answer_entity: ExerciseAnswerEntity,
    sample_incorrect_answer_entity_en: ExerciseAnswerEntity,
    sample_incorrect_answer_entity_ru: ExerciseAnswerEntity,
    sample_incorrect_answer_entity_other: ExerciseAnswerEntity,
    sample_assessor_analysis_publish_ok: PendingExerciseAnalysis,
):
    mock_exercise_repo.get_exercises_by_status.return_value = [sample_exercise]
    mock_answer_repo.get_answers_with_attempt_counts.return_value = [
        (sample_correct_answer_entity, 10),
        (sample_incorrect_answer_entity_en, 5),
        (sample_incorrect_answer_entity_ru, 3),
        (sample_incorrect_answer_entity_other, 2),
    ]
    mock_assessor.assess_pending_exercise.return_value = (
        sample_assessor_analysis_publish_ok
    )
    mock_exercise_repo.update_exercise_status_and_data.return_value = (
        sample_exercise
    )
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = AsyncMock(spec=AsyncSession)
    mock_session_context.__aexit__ = AsyncMock(return_value=False)

    with patch_processor_dependencies_manager(
        mock_exercise_repo, mock_answer_repo, mock_session_context
    ):
        stop_event = asyncio.Event()
        await exercise_review_processor(
            assessor=mock_assessor,
            stop_event=stop_event,
        )

    mock_assessor.assess_pending_exercise.assert_awaited_once()

    call_obj = mock_assessor.assess_pending_exercise.await_args_list[0]
    called_kwargs = call_obj.kwargs

    assert len(called_kwargs['correct_answers_summary']) == 1
    assert (
        called_kwargs['correct_answers_summary'][0].answer.get_answer_text()
        == 'answer'
    )
    assert called_kwargs['correct_answers_summary'][0].count == 10

    assert len(called_kwargs['user_incorrect_answers_summary']) == 2
    wrong_summary = next(
        (
            s
            for s in called_kwargs['user_incorrect_answers_summary']
            if s.answer.get_answer_text() == 'wrong'
        ),
        None,
    )
    assert wrong_summary is not None
    assert wrong_summary.count == 5 + 3
    assert wrong_summary.existing_feedback == 'Incorrect.'

    other_summary = next(
        (
            s
            for s in called_kwargs['user_incorrect_answers_summary']
            if s.answer.get_answer_text() == 'another'
        ),
        None,
    )
    assert other_summary is not None
    assert other_summary.count == 2
    assert other_summary.existing_feedback == 'Try again.'


async def test_exercise_review_processor_assessor_exception(
    mock_exercise_repo: AsyncMock,
    mock_answer_repo: AsyncMock,
    mock_assessor: AsyncMock,
    sample_exercise: ExerciseEntity,
    sample_correct_answer_entity: ExerciseAnswerEntity,
    sample_incorrect_answer_entity_en: ExerciseAnswerEntity,
):
    mock_exercise_repo.get_exercises_by_status.return_value = [sample_exercise]
    mock_answer_repo.get_answers_with_attempt_counts.return_value = [
        (sample_correct_answer_entity, 10),
        (sample_incorrect_answer_entity_en, 5),
    ]
    mock_assessor.assess_pending_exercise.side_effect = Exception(
        'Assessor failed',
    )
    mock_exercise_repo.update_exercise_status_and_data.return_value = (
        sample_exercise
    )
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = AsyncMock(spec=AsyncSession)
    mock_session_context.__aexit__ = AsyncMock(return_value=False)

    with patch_processor_dependencies_manager(
        mock_exercise_repo, mock_answer_repo, mock_session_context
    ):
        stop_event = asyncio.Event()
        decisions = await exercise_review_processor(
            assessor=mock_assessor,
            stop_event=stop_event,
        )

    mock_assessor.assess_pending_exercise.assert_awaited_once()
    mock_exercise_repo.update_exercise_status_and_data.assert_not_awaited()

    assert len(decisions) == 1
    assert decisions[0].exercise_id == sample_exercise.exercise_id
    assert decisions[0].new_status == ExerciseStatus.PENDING_REVIEW
    assert 'Assessment error: Assessor failed' in decisions[0].reason


async def test_exercise_review_processor_loop(
    mock_exercise_repo: AsyncMock,
    mock_answer_repo: AsyncMock,
    mock_assessor: AsyncMock,
    sample_exercise: ExerciseEntity,
    sample_correct_answer_entity: ExerciseAnswerEntity,
    sample_incorrect_answer_entity_en: ExerciseAnswerEntity,
    sample_assessor_analysis_publish_ok: PendingExerciseAnalysis,
):
    mock_exercise_repo.get_exercises_by_status.side_effect = [
        [sample_exercise],
        [],
        StopAsyncIteration,
    ]
    mock_answer_repo.get_answers_with_attempt_counts.return_value = [
        (sample_correct_answer_entity, 10),
        (sample_incorrect_answer_entity_en, 5),
    ]
    mock_assessor.assess_pending_exercise.return_value = (
        sample_assessor_analysis_publish_ok
    )
    mock_exercise_repo.update_exercise_status_and_data.return_value = (
        sample_exercise
    )

    stop_event = asyncio.Event()
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    async def run_and_stop():
        nonlocal mock_session
        mock_session_context = AsyncMock()
        mock_session_context.__aenter__.return_value = mock_session
        mock_session_context.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                'app.workers.exercise_review_processor.async_session_maker',
                return_value=mock_session_context,
            ),
            patch(
                'app.workers.exercise_review_processor.SQLAlchemyExerciseRepository',
                return_value=mock_exercise_repo,
            ),
            patch(
                'app.workers.exercise_review_processor.SQLAlchemyExerciseAnswerRepository',
                return_value=mock_answer_repo,
            ),
            patch(
                'app.workers.exercise_review_processor.PendingReviewAssessor',
                return_value=mock_assessor,
            ),
            patch(
                'app.workers.exercise_review_processor.EXERCISE_REVIEW_INTERVAL_SECONDS',
                0.01,
            ),
        ):
            loop_task = asyncio.create_task(
                exercise_review_processor_loop(stop_event),
            )
            # Allow time for the loop to run enough cycles to exhaust
            # side_effect and hit the StopAsyncIteration, then be stopped.
            # With interval 0.01s, 0.05s sleep allows ~5 cycles.
            # side_effect has 3 items.
            await asyncio.sleep(0.05)
            stop_event.set()
            try:
                await asyncio.wait_for(loop_task, timeout=1.0)
            except asyncio.TimeoutError:
                print('Loop task timed out during stop.')
                loop_task.cancel()
                contextlib.suppress(asyncio.CancelledError)
                await loop_task

    await run_and_stop()

    # get_exercises_by_status is called until side_effect is exhausted.
    # It's called in each cycle of the loop.
    # The number of calls will be number of loop iterations before stop_event.
    # Given 0.05s sleep and 0.01s interval, loop runs ~5 times.
    assert mock_exercise_repo.get_exercises_by_status.call_count == 5
    mock_assessor.assess_pending_exercise.assert_awaited_once()
    mock_exercise_repo.update_exercise_status_and_data.assert_awaited_once()

    # Commit is called after the first cycle (with exercise)
    # and the second cycle (no exercises).
    # Not called in subsequent cycles due to StopAsyncIteration before commit.
    assert mock_session.commit.await_count == 2
    # Rollback is called when StopAsyncIteration is caught.
    # This will happen for the 3rd, 4th,
    # and 5th calls to get_exercises_by_status.
    assert mock_session.rollback.await_count == 3
