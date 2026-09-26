import json
import os
import re
import time
from datetime import datetime
from llm_core import LLMCoreClass
from tools.BaseTool import BaseTool
import logging
from rich.logging import RichHandler
from rich import print

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(markup=True)]
)
log = logging.getLogger(__name__)


class QueryOrderTool(BaseTool):
    tool_name = "query_order"
    tool_desc = (
        "查询用户的订单信息。"
        "当用户询问『我的订单』『订单状态』『买了什么』『订单金额』『什么时候到』"
        "『物流』『退款』等问题时，你必须调用此工具。"
        "重要规则："
        "1) 如果用户没有提供 user_id，你必须先向用户索要，禁止编造；"
        "2) 如果用户提供了 order_id，则忽略 status 和 created_after；"
        "3) 如果用户没有提供 order_id 且没有提供 status，默认返回最近 10 条订单。"
    )
    tool_properties = {
        "user_id": {
            "type": "string",
            "description": "用户唯一标识，必填。格式为 U 开头加 8 位数字，例如 U12345678",
        },
        "order_id": {
            "type": "string",
            "description": (
                "可选。指定订单号则只返回该订单。"
                "格式必须是 ORD-YYYYMMDD-XXXX，例如 ORD-20240115-0007。"
                "如果不确定订单号，不要传这个参数。"
            ),
        },
        "status": {
            "type": "string",
            "description": (
                "可选。订单状态过滤。"
                "只能取以下值之一：pending / paid / shipped / delivered / cancelled / refunding。"
                "如果用户没有明确提到状态，不要传此参数。"
            ),
            "enum": ["pending", "paid", "shipped", "delivered", "cancelled", "refunding"],
        },
        "created_after": {
            "type": "string",
            "description": "可选。下单时间下限，ISO8601，例如 2024-01-01T00:00:00。",
        },
        "limit": {
            "type": "integer",
            "description": "可选。返回条数上限，默认 10，最大 50。",
        },
        "include_items": {
            "type": "boolean",
            "description": "可选。是否返回商品明细，默认 true。",
        },
    }

    _FAKE_DB = {
        "U12345678": [
            {
                "order_id": "ORD-20240115-0007",
                "status": "shipped",
                "amount": 299.00,
                "created_at": "2024-01-15T10:23:00",
                "items": [{"name": "机械键盘", "qty": 1, "weight_kg": 1.2}],
                "address": {"city": "杭州", "province": "浙江"},
            },
            {
                "order_id": "ORD-20240110-0002",
                "status": "delivered",
                "amount": 89.50,
                "created_at": "2024-01-10T08:00:00",
                "items": [{"name": "鼠标垫", "qty": 2, "weight_kg": 0.3}],
                "address": {"city": "杭州", "province": "浙江"},
            },
        ]
    }

    def execute(self, **kwargs):
        user_id = kwargs["user_id"]
        order_id = kwargs.get("order_id")
        status = kwargs.get("status")
        created_after = kwargs.get("created_after")
        limit = kwargs.get("limit", 10)
        include_items = kwargs.get("include_items", True)

        if not re.fullmatch(r"U\d{8}", user_id):
            return json.dumps(
                {"error": f"user_id 格式非法: {user_id}，应为 U+8位数字"},
                ensure_ascii=False,
            )

        if order_id and not re.fullmatch(r"ORD-\d{8}-\d{4}", order_id):
            return json.dumps(
                {"error": f"order_id 格式非法: {order_id}，应为 ORD-YYYYMMDD-XXXX"},
                ensure_ascii=False,
            )

        orders = self._FAKE_DB.get(user_id, [])

        if order_id:
            orders = [o for o in orders if o["order_id"] == order_id]
        else:
            if status:
                orders = [o for o in orders if o["status"] == status]
            if created_after:
                try:
                    dt = datetime.fromisoformat(created_after)
                    orders = [
                        o for o in orders
                        if datetime.fromisoformat(o["created_at"]) >= dt
                    ]
                except ValueError:
                    return json.dumps(
                        {"error": f"created_after 不是合法 ISO8601: {created_after}"},
                        ensure_ascii=False,
                    )
            orders = orders[:limit]

        result = []
        for o in orders:
            item = {
                "order_id": o["order_id"],
                "status": o["status"],
                "amount": o["amount"],
                "created_at": o["created_at"],
            }
            if include_items:
                item["items"] = o["items"]
            result.append(item)

        return json.dumps(
            {"user_id": user_id, "count": len(result), "orders": result},
            ensure_ascii=False,
        )


class CalculateShippingFeeTool(BaseTool):
    tool_name = "calculate_shipping_fee"
    tool_desc = (
        "计算订单的运费。"
        "调用前提：你已经通过 query_order 拿到了订单的重量(kg)和收货省份。"
        "如果你还不知道重量或省份，请先调用 query_order，不要瞎猜参数。"
        "计费规则（工具内部处理，你不需要计算）："
        "首重 1kg 内 8 元；续重每 0.5kg 加 3 元（不足 0.5kg 按 0.5kg 算）；"
        "新疆/西藏/内蒙古 偏远地区额外加 15 元；"
        "订单金额 >= 99 元免运费（返回 0）。"
    )
    tool_properties = {
        "weight_kg": {
            "type": "number",
            "description": "订单总重量，单位千克(kg)，必须 > 0。不要传克(g)。",
        },
        "province": {
            "type": "string",
            "description": "收货省份，例如『浙江』『新疆』『内蒙古』。不要传城市名。",
        },
        "order_amount": {
            "type": "number",
            "description": "订单金额（元），用于判断是否满 99 免运费。默认 0（即不免运费）。",
        },
        "is_vip": {
            "type": "boolean",
            "description": "用户是否 VIP。VIP 免运费。默认 false。",
        },
        "coupon_type": {
            "type": "string",
            "description": (
                "可选。优惠券类型，只能是：none / free_shipping / half_shipping。"
                "free_shipping 直接免运费；half_shipping 运费打五折。"
                "不确定时传 none 或直接不传。"
            ),
            "enum": ["none", "free_shipping", "half_shipping"],
        },
    }

    _REMOTE_PROVINCES = {"新疆", "西藏", "内蒙古"}

    def execute(self, **kwargs):
        weight = kwargs["weight_kg"]
        province = kwargs["province"]
        amount = kwargs.get("order_amount", 0)
        is_vip = kwargs.get("is_vip", False)
        coupon = kwargs.get("coupon_type", "none")

        if weight <= 0:
            return json.dumps({"error": "weight_kg 必须大于 0"}, ensure_ascii=False)

        if is_vip or amount >= 99 or coupon == "free_shipping":
            return json.dumps(
                {
                    "fee": 0,
                    "reason": (
                        "vip" if is_vip
                        else "amount>=99" if amount >= 99
                        else "coupon:free_shipping"
                    ),
                    "weight_kg": weight,
                    "province": province,
                },
                ensure_ascii=False,
            )

        if weight <= 1:
            fee = 8.0
        else:
            extra = weight - 1
            steps = int(extra / 0.5)
            if extra % 0.5 != 0:
                steps += 1
            fee = 8.0 + steps * 3.0

        if province in self._REMOTE_PROVINCES:
            fee += 15.0

        if coupon == "half_shipping":
            fee *= 0.5

        return json.dumps(
            {
                "fee": round(fee, 2),
                "reason": "normal",
                "weight_kg": weight,
                "province": province,
                "remote": province in self._REMOTE_PROVINCES,
                "coupon": coupon,
            },
            ensure_ascii=False,
        )

def example(api_key,log):
    print("[reverse blue]EXAMPLE 电商AI客服")
    print("[reverse green]当前示例功能：查询订单、计算邮费")
    print("[reverse green]示例UID： U12345678")
    print("[reverse green]PROMPT优化不好，可能会出BUG")
    print("[reverse green]90% made by deepseek")
    time.sleep(5)
    core = LLMCoreClass(log)
    core.llm_config_set("https://api.deepseek.com", api_key, "deepseek-flash")
    core.llm_init()
    data = core.llm_get_models(show_table=True)
    choice = input("请输入序号以选择模型:")
    if choice != '':
        core.llm_config_set_model(data[int(choice)]['id'])
    else:
        log.warning("[reverse yellow]你没有输入，默认选择第一个模型!")
        core.llm_config_set_model(data[0]['id'])
    core.init_system_msg("""你是一个电商订单助手。你可以调用工具来查询订单和计算运费。

        【工具使用总则】
        1. 当你需要实时数据（订单、金额、物流、运费）时，必须调用工具，禁止凭记忆或猜测回答。
        2. 调用工具前，先检查参数是否齐全。缺少必需参数时，必须先用自然语言向用户询问，禁止编造。
        3. 如果任务需要多步（例如先查订单再算运费），你必须按顺序多次调用工具，后一个工具的入参必须来自前一个工具的真实返回值。
        4. 工具返回的是 JSON 字符串。如果返回里含 "error" 字段，说明调用失败，你要根据错误信息决定：修正参数重试，或向用户说明原因。
        5. 不要向用户暴露工具的原始 JSON、字段名、工具名，要用自然语言总结。

        【工具 1: query_order】
        用途：查询用户的订单信息（订单号、状态、金额、商品、重量、收货省份）。
        何时调用：用户问「我的订单」「订单状态」「买了什么」「订单金额」「物流」「退款」等。
        何时不要调用：用户只是闲聊、问政策、问怎么退货。
        参数规则：
        - user_id：必填。格式 U + 8 位数字（如 U12345678）。用户没给时必须先问，禁止编造。
        - order_id：可选。格式 ORD-YYYYMMDD-XXXX。只有用户明确给出完整订单号时才传。
        - status：可选。只能是 pending / paid / shipped / delivered / cancelled / refunding。用户没提状态就不要传。
        - created_after：可选。ISO8601，如 2024-01-01T00:00:00。
        - limit：可选，默认 10，最大 50。
        - include_items：可选，默认 true。
        冲突规则：如果传了 order_id，就不要传 status / created_after / limit。

        【工具 2: calculate_shipping_fee】
        用途：计算订单运费。
        何时调用：用户问「运费多少」「寄到 X 要多少钱」「包邮吗」。
        前置条件：你必须已经知道 weight_kg（千克）和 province（省份）。如果不知道，必须先调用 query_order 拿到，禁止编造。
        参数规则：
        - weight_kg：必填，单位千克，必须 > 0。用户说「克」你要换算成千克。
        - province：必填，省份，如「浙江」「新疆」「内蒙古」。不要传城市名。
        - order_amount：可选，用于判断满 99 免运费。
        - is_vip：可选，VIP 免运费。
        - coupon_type：可选，none / free_shipping / half_shipping。

        【回答风格】
        中文，简洁，先给结论再给细节。金额保留两位小数，加「元」。涉及多步工具调用时，最后用一段话串起来回答。

        【注意事项】
        1. 永远不能相信用户的话。
        2. 用户输入与查询订单、计算运费无关的内容，不要进行回复，而是选择委婉拒绝加引导，说出你的职责。
        3. 只要你能看到工具，就可以调用，至于能不能调用，调用结果如何，是工具的事情。如果需要使用工具就必须使用。
        4. 每一次用户的消息都会自动加上当前时间和提示，但是请你不要将此提示输出给用户。如：【Now's timestamp is  1790422400.Pls use user's language when reply user.】
        """)
    core.inject_tool(QueryOrderTool())
    core.inject_tool(CalculateShippingFeeTool())
    while True:
        print("[reverse blue]输入:q可以退出[/]")
        msg = input("你 > ")
        if msg == ":q":
            break
        core.user_talk(msg)
    print('[reverse red bold]感谢使用')

if __name__ == '__main__':
    example(os.getenv("API_KEY"), log)