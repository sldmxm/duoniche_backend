import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.user import User
from app.db.models.user import User as UserModel


@pytest.mark.asyncio
async def test_get_or_create_user_new_user(
    client: AsyncClient, async_session: AsyncSession
):
    """Test creating a new user."""
    user_data = {
        'telegram_id': '98765',
        'username': 'newuser',
        'name': 'New User',
        'user_language': 'en',
        'target_language': 'en',
    }
    response = await client.put('/api/v1/users/', json=user_data)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data['telegram_id'] == user_data['telegram_id']
    assert response_data['username'] == user_data['username']
    assert response_data['name'] == user_data['name']
    assert response_data['user_language'] == user_data['user_language']
    assert response_data['target_language'] == user_data['target_language']
    assert response_data['user_id'] is not None

    # Check if the user was created in the database
    db_user = await async_session.get(UserModel, response_data['user_id'])
    assert db_user is not None
    assert db_user.telegram_id == user_data['telegram_id']
    assert db_user.username == user_data['username']
    assert db_user.name == user_data['name']
    assert db_user.user_language == user_data['user_language']
    assert db_user.target_language == user_data['target_language']


@pytest.mark.asyncio
async def test_get_or_create_user_existing_user(
    client: AsyncClient, async_session: AsyncSession, user: User, add_db_user
):
    """Test getting an existing user."""
    user_data = {
        'telegram_id': user.telegram_id,
        'username': 'updateduser',
        'name': 'Updated User',
        'user_language': 'ru',
        'target_language': 'ru',
    }
    response = await client.put('/api/v1/users/', json=user_data)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data['user_id'] == user.user_id
    assert response_data['telegram_id'] == user.telegram_id
    assert response_data['username'] == user.username
    assert response_data['name'] == user.name
    assert response_data['user_language'] == user.user_language
    assert response_data['target_language'] == user.target_language

    # Check if the user was not updated in the database
    db_user = await async_session.get(UserModel, response_data['user_id'])
    assert db_user is not None
    assert db_user.telegram_id == user.telegram_id
    assert db_user.username == user.username
    assert db_user.name == user.name
    assert db_user.user_language == user.user_language
    assert db_user.target_language == user.target_language


@pytest.mark.asyncio
async def test_get_user_by_telegram_id_success(
    client: AsyncClient,
    user: User,
    add_db_user,
):
    """Test getting a user by telegram_id."""
    response = await client.get(f'/api/v1/users/{user.telegram_id}')
    assert response.status_code == 200
    response_data = response.json()
    assert response_data['user_id'] == add_db_user.user_id
    assert response_data['telegram_id'] == add_db_user.telegram_id
    assert response_data['username'] == add_db_user.username
    assert response_data['name'] == add_db_user.name
    assert response_data['user_language'] == add_db_user.user_language
    assert response_data['target_language'] == add_db_user.target_language


@pytest.mark.asyncio
async def test_get_user_by_telegram_id_not_found(client: AsyncClient):
    """Test getting a non-existent user by telegram_id."""
    response = await client.get('/api/v1/users/99999')
    assert response.status_code == 404
    assert response.json()['detail'] == 'User not found'
