from typing import TypedDict, NotRequired

class StyleChatState(TypedDict):
    user_input: str
    emotion: NotRequired[str]
    reply_style: NotRequired[str]
    reply: NotRequired[str]