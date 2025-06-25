import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.db.models.payment import DBPayment as PaymentModel
from app.db.models.user_bot_profile import (
    DBUserBotProfile as UserBotProfileModel,
)
from app.db.models.user_report import UserReport as UserReportModel

pytestmark = pytest.mark.asyncio


async def test_get_invoice_details_session_unlock(
    client: AsyncClient, add_db_user, add_user_bot_profile
):
    user = add_db_user
    profile = add_user_bot_profile

    response = await client.get(
        f'/api/v1/payments/invoice-details/session_unlock/users/{user.user_id}/bots/{profile.bot_id}'
    )

    assert response.status_code == 200
    data = response.json()
    assert data['title'] == '☕️ Support'
    assert 'invoice_payload' in data
    payload = data['invoice_payload']
    assert 'session_unlock' in payload
    assert str(user.user_id) in payload
    assert str(profile.bot_id) in payload


async def test_get_invoice_details_report_donation(
    client: AsyncClient, db_session, add_db_user, add_user_bot_profile
):
    user = add_db_user
    profile = add_user_bot_profile

    report = UserReportModel(
        user_id=user.user_id,
        bot_id=profile.bot_id,
        week_start_date=date(2024, 1, 1),
        short_report='Test short report',
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.get(
        f'/api/v1/payments/invoice-details/report_donation/users/{user.user_id}/bots/{profile.bot_id}?item_id={report.report_id}'
    )

    assert response.status_code == 200
    data = response.json()
    assert data['title'] == '☕️ Support'
    assert 'invoice_payload' in data
    payload = data['invoice_payload']
    assert 'report_donation' in payload
    assert str(report.report_id) in payload


@pytest.mark.parametrize(
    'url_part, expected_status, expected_detail_part',
    [
        (
            'report_donation/users/9999/bots/Bulgarian',
            400,
            'No profile found',
        ),
        ('session_unlock/users/1/bots/InvalidBot', 422, 'Invalid bot_id'),
        (
            'invalid_source/users/1/bots/Bulgarian',
            400,
            'Unsupported payment source',
        ),
        (
            'report_donation/users/1/bots/Bulgarian',
            400,
            'item_id (report_id) is required',
        ),
    ],
)
async def test_get_invoice_details_errors(
    client: AsyncClient,
    add_db_user,
    add_user_bot_profile,
    url_part,
    expected_status,
    expected_detail_part,
):
    user = add_db_user
    url = (
        f"/api/v1/payments/invoice-details/"
        f"{url_part.replace('1', str(user.user_id))}"
    )

    response = await client.get(url)

    assert response.status_code == expected_status
    assert expected_detail_part in response.json()['detail']


async def test_process_payment_session_unlock(
    client: AsyncClient,
    db_session,
    add_db_user,
    user_bot_profile_service,
):
    bot_id = 'Bulgarian'
    user = add_db_user
    await user_bot_profile_service.get_or_create(user.user_id, bot_id, 'en')
    await user_bot_profile_service.update_session(
        user_id=user.user_id,
        bot_id=bot_id,
        session_frozen_until=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    invoice_payload = (
        f'invoice_payload:session_unlock:{user.user_id}'
        f':{bot_id}:-1:{int(datetime.now(timezone.utc).timestamp())}'
    )
    payment_data = {
        'telegram_payment_charge_id': str(uuid.uuid4()),
        'amount': 100,
        'invoice_payload': invoice_payload,
        'currency': 'XTR',
    }

    response = await client.post('/api/v1/payments/process', json=payment_data)

    assert response.status_code == 200
    assert response.json()['message'] == 'Payment processed successfully.'

    # Check DB
    payment = await db_session.scalar(
        select(PaymentModel).where(
            PaymentModel.telegram_payment_charge_id
            == payment_data['telegram_payment_charge_id']
        )
    )
    assert payment is not None
    assert payment.user_id == user.user_id

    profile = await db_session.get(UserBotProfileModel, (user.user_id, bot_id))
    assert profile.session_frozen_until is None


async def test_process_duplicate_payment(
    client: AsyncClient, db_session, add_db_user, add_user_bot_profile
):
    bot_id = 'Bulgarian'
    user = add_db_user
    invoice_payload = (
        f'invoice_payload'
        f':session_unlock'
        f':{user.user_id}'
        f':{bot_id}:-1'
        f':{int(datetime.now(timezone.utc).timestamp())}'
    )
    payment_data = {
        'telegram_payment_charge_id': str(uuid.uuid4()),
        'amount': 100,
        'invoice_payload': invoice_payload,
        'currency': 'XTR',
    }

    # First request
    response1 = await client.post(
        '/api/v1/payments/process', json=payment_data
    )

    print(response1.json())
    assert response1.status_code == 200
    assert response1.json()['message'] == 'Payment processed successfully.'

    # Second request
    response2 = await client.post(
        '/api/v1/payments/process', json=payment_data
    )
    assert response2.status_code == 200
    assert response2.json()['message'] == 'Payment already processed.'

    # Check DB
    result = await db_session.execute(
        select(func.count()).select_from(PaymentModel)
    )
    assert result.scalar_one() == 1


async def test_process_payment_invalid_payload(client: AsyncClient):
    payment_data = {
        'telegram_payment_charge_id': str(uuid.uuid4()),
        'amount': 100,
        'invoice_payload': 'invalid:payload_format',
        'currency': 'XTR',
    }

    response = await client.post('/api/v1/payments/process', json=payment_data)

    assert response.status_code == 400
    assert 'Invalid payment payload or data' in response.json()['detail']
