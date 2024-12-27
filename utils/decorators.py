import logging
from functools import wraps

active_commands = {}  # Global dictionary to track active commands


def command_in_progress():
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            ctx = args[1]  # Context is typically the second argument in a command
            user_id = ctx.author.id

            if user_id in active_commands:
                await ctx.send(
                    "❌ You already have an active command running. Please finish it before starting another.")
                return

            active_commands[user_id] = True  # Mark the command as active
            try:
                return await func(*args, **kwargs)
            finally:
                active_commands.pop(user_id, None)  # Ensure cleanup after command finishes

        return wrapper

    return decorator

