import json
from abc import abstractmethod

class BaseTool:
    tool_name = None
    tool_desc = None
    tool_properties = None
    """
    tool_properties e.g.
    ```
    {
        "location": {
            "type": "string",   [object|string|number|integer|boolean|array|enum|anyOf] 详细见https://api-docs.deepseek.com/zh-cn/guides/tool_calls
            "description": "The city and state, e.g. San Francisco, CA",
        }
    }
    ```
    """

    def __init_subclass__(cls, **kwargs):
        """
        在这里检查子类是否定义所有所需变量
        :param kwargs:
        :return:
        """
        super().__init_subclass__(**kwargs)
        needs = ["tool_name", "tool_desc", "tool_properties"]
        for need in needs:
            if getattr(cls, need, None) is None:
                raise TypeError(
                    f"{cls.__name__}没有初始化'{need}'参数"
                )

    @abstractmethod
    def execute(self, **kwargs):
        """
        子函数实现的工具执行类
        :param kwargs:
        :return:
        """
        raise NotImplementedError

    def validate(self, arguments):
        """检查 JSON 参数是否符合 schema，返回清洗后的参数"""
        if not isinstance(arguments, dict):
            raise TypeError(f"{self.tool_name}: arguments 必须是 dict")

        cleaned = {}
        for key, rule in self.tool_properties.items():
            required = rule.get("required", False)
            expected_type_name = rule.get("type")  # 字符串，如 "string"
            default = rule.get("default")

            if key not in arguments:
                if required:
                    raise ValueError(f"{self.tool_name}: 缺少必需参数 '{key}'")
                if default is not None:
                    cleaned[key] = default
                continue

            value = arguments[key]

            # 把 schema 类型名转成 Python 类型
            JSON_TYPE_MAP = {
                "string": str,
                "integer": int,
                "number": (int, float),  # number 允许 int 或 float
                "boolean": bool,
                "object": dict,
                "array": list,
                "null": type(None),
            }
            expected_type = JSON_TYPE_MAP.get(expected_type_name)

            if expected_type is not None and not isinstance(value, expected_type):
                raise TypeError(
                    f"{self.tool_name}: 参数 '{key}' 期望 {expected_type_name}，"
                    f"实际是 {type(value).__name__}"
                )
            cleaned[key] = value

        extra = set(arguments) - set(self.tool_properties)
        if extra:
            raise ValueError(f"{self.tool_name}: 未知参数 {extra}")

        return cleaned

    def __call__(self, arguments_str):
        arguments = json.loads(arguments_str)
        cleaned = self.validate(arguments)
        return self.execute(**cleaned)
