# class UserMiddleware(BaseMiddleware):
#     async def __call__(
#         self,
#         handler: Callable[[Message, dict[str, Any]], Any],
#         event: Message,
#         data: dict[str, Any],
#     ) -> Any:
#         async for session in get_async_session():
#             user = await user_repository.get_by_telegram_id(
#                 event.from_user.id)
#             if not user:
#                 await event.answer("Please use /start command")
#                 return
#             data['user'] = user
#             return await handler(event, data)
