from app.core.entities.user_settings import UserSettings

FREE_PLAN_SETTINGS = UserSettings()

TRIAL_PLAN_SETTINGS = UserSettings(
    min_session_interval_minutes=0,
)

PREMIUM_PLAN_SETTINGS = UserSettings(
    min_session_interval_minutes=0,
)
