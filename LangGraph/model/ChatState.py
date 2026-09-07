from typing import TypedDict, NotRequired


class ChatState(TypedDict):
    user_input:str
    emotion:NotRequired[str]
    reply: NotRequired[str]