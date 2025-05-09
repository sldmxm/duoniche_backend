import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.consts import DEFAULT_LANGUAGE_LEVEL, DEFAULT_USER_LANGUAGE
from app.core.entities.user import User
from app.core.entities.user_bot_profile import BotID, UserStatusInBot
from app.db.models.user import User as UserModel
from app.db.models.user_bot_profile import (
    DBUserBotProfile as UserBotProfileModel,
)


@pytest.mark.asyncio
async def test_get_or_create_user_new_user(
    client: AsyncClient, async_session: AsyncSession
):
    user_data = {
        'telegram_id': '98765',
        'username': 'newuser',
        'name': 'New User',
        'user_language': 'en',
        'target_language': BotID.BG.value,
        'telegram_data': {'test': 'test'},
    }
    response = await client.put('/api/v1/users/', json=user_data)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data['telegram_id'] == user_data['telegram_id']
    assert response_data['username'] == user_data['username']
    assert response_data['name'] == user_data['name']
    assert response_data['user_language'] == user_data['user_language']

    assert response_data['user_id'] is not None
    assert response_data['plan'] is None
    assert response_data['language_level'] == DEFAULT_LANGUAGE_LEVEL.value

    db_user = await async_session.get(UserModel, response_data['user_id'])
    assert db_user is not None
    assert db_user.telegram_id == user_data['telegram_id']
    assert db_user.username == user_data['username']
    assert db_user.name == user_data['name']
    assert db_user.plan is None

    db_profile = await async_session.get(
        UserBotProfileModel, (response_data['user_id'], BotID.BG)
    )
    assert db_profile is not None
    assert db_profile.user_language == user_data['user_language']
    assert db_profile.bot_id == BotID.BG
    assert db_profile.language_level == DEFAULT_LANGUAGE_LEVEL
    assert db_profile.status == UserStatusInBot.ACTIVE


@pytest.mark.asyncio
async def test_get_or_create_user_existing_user(
    client: AsyncClient, async_session: AsyncSession, user: User, add_db_user
):
    user_data = {
        'telegram_id': user.telegram_id,
        'username': 'updateduser',
        'name': 'Updated User',
        'user_language': 'ru',
        'target_language': BotID.BG.value,
        'telegram_data': {'test': 'test'},
    }
    response = await client.put('/api/v1/users/', json=user_data)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data['user_id'] == user.user_id
    assert response_data['telegram_id'] == user.telegram_id
    assert response_data['username'] == user.username
    assert response_data['name'] == user.name
    assert response_data['user_language'] == user_data['user_language']
    assert response_data['plan'] is None
    assert response_data['language_level'] == DEFAULT_LANGUAGE_LEVEL.value

    db_user = await async_session.get(UserModel, response_data['user_id'])
    db_profile = await async_session.get(
        UserBotProfileModel, (response_data['user_id'], BotID.BG)
    )
    assert db_user is not None
    assert db_user.telegram_id == user.telegram_id
    assert db_user.username == user.username
    assert db_user.name == user.name
    assert db_user.plan is None
    assert db_profile.user_language == user_data['user_language']
    assert db_profile.bot_id == BotID.BG
    assert db_profile.language_level == DEFAULT_LANGUAGE_LEVEL


@pytest.mark.asyncio
async def test_get_user_by_telegram_id_success(
    client: AsyncClient,
    user: User,
    add_db_user,
    add_user_bot_profile,
):
    response = await client.get(
        f'/api/v1/users/by-telegram-id/{user.telegram_id}'
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data['user_id'] == user.user_id
    assert response_data['telegram_id'] == user.telegram_id
    assert response_data['username'] == user.username
    assert response_data['name'] == user.name
    assert response_data['user_language'] == add_user_bot_profile.user_language
    assert response_data['plan'] == user.plan
    assert (
        response_data['language_level']
        == add_user_bot_profile.language_level.value
    )


@pytest.mark.asyncio
async def test_get_user_by_telegram_id_not_found(client: AsyncClient):
    response = await client.get('/api/v1/users/by-telegram-id/99999')
    assert response.status_code == 404
    assert response.json()['detail'] == 'User not found'


@pytest.mark.asyncio
async def test_update_user_by_user_id_success(
    client: AsyncClient,
    async_session: AsyncSession,
    user: User,
    add_db_user,
    add_user_bot_profile,
):
    updated_user_data = {
        'user_id': user.user_id,
        'telegram_id': user.telegram_id,
        'username': 'updateduser',
        'name': 'Updated User',
        'user_language': 'ru',
        'target_language': BotID.BG.value,
        'telegram_data': {'test': 'test'},
    }
    response = await client.put(
        f'/api/v1/users/{user.user_id}', json=updated_user_data
    )

    assert response.status_code == 200
    response_data = response.json()

    assert response_data['user_id'] == user.user_id
    assert response_data['telegram_id'] == user.telegram_id
    assert response_data['username'] == updated_user_data['username']
    assert response_data['name'] == updated_user_data['name']
    assert response_data['user_language'] == updated_user_data['user_language']
    assert response_data['plan'] == user.plan
    assert response_data['cohort'] == user.cohort
    assert (
        response_data['language_level']
        == add_user_bot_profile.language_level.value
    )

    db_user = await async_session.get(UserModel, response_data['user_id'])
    db_profile = await async_session.get(
        UserBotProfileModel, (response_data['user_id'], BotID.BG)
    )
    assert db_user is not None
    assert db_user.telegram_id == user.telegram_id
    assert db_user.username == updated_user_data['username']
    assert db_user.name == updated_user_data['name']
    assert db_profile.user_language == updated_user_data['user_language']
    assert db_profile.bot_id == BotID.BG
    assert (
        db_profile.language_level == add_user_bot_profile.language_level
    )  # language_level is not updated by this endpoint


@pytest.mark.asyncio
async def test_update_user_by_user_id_not_found(client: AsyncClient):
    user_data = {
        'user_id': 157,
        'telegram_id': '99999',
        'username': 'updateduser',
        'name': 'Updated User',
        'user_language': 'ru',
        'target_language': BotID.BG.value,
        'language_level': 'B1',
        'telegram_data': {'test': 'test'},
    }
    response = await client.put('/api/v1/users/157', json=user_data)
    assert response.status_code == 404
    assert response.json()['detail'] == 'User 157 does not exist'


@pytest.mark.asyncio
async def test_get_next_action_legacy_path_success(
    client,
    user_id_for_sample_request,
    db_sample_exercise,
    add_db_user,
    add_user_bot_profile,
):
    user_id = user_id_for_sample_request
    response = await client.get(
        f'/api/v1/users/{user_id}/next_action/',
    )

    print(response.json())

    assert response.status_code == 200
    response_data = response.json()
    assert response_data['action'] is not None
    if response_data['exercise']:
        assert (
            response_data['exercise']['exercise_id']
            == db_sample_exercise.exercise_id
        )


@pytest.mark.asyncio
async def test_get_next_action_new_path_success(
    client,
    user_id_for_sample_request,
    db_sample_exercise,
    add_db_user,
    add_user_bot_profile,
):
    user_id = user_id_for_sample_request
    bot_id_value = (
        add_user_bot_profile.bot_id.value
    )  # Use the bot from the profile fixture
    # This calls the new endpoint /{user_id}/bots/{bot_id}/next-action/
    response = await client.get(
        f'/api/v1/users/{user_id}/bots/{bot_id_value}/next-action/',
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data['action'] is not None
    if response_data['exercise']:
        assert (
            response_data['exercise']['exercise_id']
            == db_sample_exercise.exercise_id
        )


@pytest.mark.asyncio
async def test_get_next_action_legacy_path_invalid_user_id(
    client: AsyncClient,
):
    # Test invalid user_id on the legacy path
    response = await client.get(
        '/api/v1/users/TEST/next_action/',
    )
    assert response.status_code == 422
    assert (
        response.json()['detail'][0]['msg']
        == 'Input should be a valid integer, '
        'unable to parse string as an integer'
    )
    assert response.json()['detail'][0]['loc'] == [
        'path',
        'user_id',
    ]


@pytest.mark.asyncio
async def test_get_next_action_new_path_invalid_bot_id(
    client: AsyncClient, add_db_user: UserModel
):
    user_id = add_db_user.user_id
    invalid_bot_id_value = 'INVALID_BOT'
    response = await client.get(
        f'/api/v1/users/{user_id}/bots/{invalid_bot_id_value}/next-action/',
    )

    assert response.status_code == 422
    assert response.json()['detail'].startswith('Invalid bot_id in path:')


@pytest.mark.asyncio
async def test_block_bot_success(
    client: AsyncClient,
    async_session: AsyncSession,
    add_db_user: UserModel,
    add_user_bot_profile: UserBotProfileModel,
):
    user_id = add_db_user.user_id
    bot_to_block = add_user_bot_profile.bot_id
    bot_id_value_for_url = bot_to_block.value
    reason = 'User blocked the bot via notifier'

    payload = {'telegram_id': add_db_user.telegram_id, 'reason': reason}

    response = await client.post(
        f'/api/v1/users/{user_id}/bots/{bot_id_value_for_url}/block/',
        json=payload,
    )

    assert response.status_code == 200, response.text
    response_data = response.json()
    assert response_data == {'status': 'ok'}

    db_profile = await async_session.get(
        UserBotProfileModel, (user_id, bot_to_block)
    )
    assert db_profile is not None
    assert db_profile.status == UserStatusInBot.BLOCKED
    assert db_profile.reason == reason
    assert db_profile.user_id == user_id
    assert db_profile.bot_id == bot_to_block
    assert (
        db_profile.user_language == add_user_bot_profile.user_language
    )  # Check against existing profile data
    assert (
        db_profile.language_level == add_user_bot_profile.language_level
    )  # Check against existing profile data


@pytest.mark.asyncio
async def test_block_bot_user_not_found_by_path_id(client: AsyncClient):
    non_existent_user_id = 999999
    bot_id_value_for_url = BotID.BG.value
    payload = {'telegram_id': '1234567', 'reason': 'Test reason'}

    response = await client.post(
        f'/api/v1/users/{non_existent_user_id}/bots/{bot_id_value_for_url}/block/',
        json=payload,
    )
    assert response.status_code == 404
    assert response.json()['detail'] == 'User not found'


@pytest.mark.asyncio
async def test_block_bot_telegram_id_mismatch(
    client: AsyncClient, add_db_user: UserModel
):
    user_id = add_db_user.user_id
    correct_telegram_id = int(add_db_user.telegram_id)
    mismatched_telegram_id = str(correct_telegram_id + 1)
    bot_id_value_for_url = BotID.BG.value

    payload = {
        'telegram_id': mismatched_telegram_id,
        'reason': 'Test reason with mismatched telegram_id',
    }

    response = await client.post(
        f'/api/v1/users/{user_id}/bots/{bot_id_value_for_url}/block/',
        json=payload,
    )
    assert response.status_code == 404
    assert response.json()['detail'] == 'User not found'


@pytest.mark.asyncio
async def test_block_bot_invalid_bot_id_value(
    client: AsyncClient, add_db_user: UserModel
):
    user_id = add_db_user.user_id
    invalid_bot_id_value_for_url = 'INVALID_BOT_ID_STRING'

    payload = {
        'telegram_id': add_db_user.telegram_id,
        'reason': 'Test reason with invalid bot_id',
    }

    response = await client.post(
        f'/api/v1/users/{user_id}/bots/{invalid_bot_id_value_for_url}/block/',
        json=payload,
    )
    # Expect 422 from FastAPI's automatic Enum validation
    assert response.status_code == 422
    # The expected error message depends on the actual BotID values
    assert (
        response.json()['detail'][0]['msg']
        == "Input should be 'Bulgarian' or 'Serbian'"
    )
    assert response.json()['detail'][0]['loc'] == ['path', 'bot_id']


@pytest.mark.asyncio
async def test_block_bot_creates_profile_if_not_exists_and_blocks(
    client: AsyncClient, async_session: AsyncSession, add_db_user: UserModel
):
    user_id = add_db_user.user_id
    bot_to_block = BotID.BG
    bot_id_value_for_url = bot_to_block.value
    reason = 'Blocking creates profile'

    # Ensure profile does NOT exist initially
    existing_profile = await async_session.get(
        UserBotProfileModel, (user_id, bot_to_block)
    )
    if existing_profile:
        await async_session.delete(existing_profile)
        await async_session.commit()
        assert (
            await async_session.get(
                UserBotProfileModel, (user_id, bot_to_block)
            )
            is None
        )

    payload = {'telegram_id': add_db_user.telegram_id, 'reason': reason}

    response = await client.post(
        f'/api/v1/users/{user_id}/bots/{bot_id_value_for_url}/block/',
        json=payload,
    )

    assert response.status_code == 200, response.text
    assert response.json() == {'status': 'ok'}

    # Verify profile was created and blocked
    db_profile = await async_session.get(
        UserBotProfileModel, (user_id, bot_to_block)
    )
    assert db_profile is not None
    assert db_profile.status == UserStatusInBot.BLOCKED
    assert db_profile.reason == reason
    assert db_profile.user_id == user_id
    assert db_profile.bot_id == bot_to_block
    # Check default values for newly created profile
    assert db_profile.user_language == DEFAULT_USER_LANGUAGE
    assert db_profile.language_level == DEFAULT_LANGUAGE_LEVEL
