from typing import TypedDict


class OrderState(TypedDict):
    raw_message: str         # 用户原始消息
    dish: str                # 菜品名称
    address: str            # 配送地址
    confirmed: bool
    # 用户是否确认
    dispatch_result: str     # 派单结果