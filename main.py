"""
Author: Pumpkin
Date: 2026 -09 -25
"""
import json
import logging
import shutil
import time
from abc import abstractmethod

from docutils.nodes import caption
from openpyxl.descriptors import Typed
from rich.panel import Panel
from rich.table import Table

from funcs.create_logger import create_logger
from rich.console import Console
from rich import traceback
from rich import print
from funcs.dbf import *
import rich
from core.settings import *
from openai import OpenAI
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()
traceback.install(show_locals=True)
MAX_WIDTH = 100
console = Console(width=min(MAX_WIDTH, shutil.get_terminal_size().columns))

log = create_logger()


# 后面再写
# def main():
#     # database = dbf("./subject_tester.db")
#     while True:
#         print("[bold blue]请输入菜单前面的数字，进行操作:")
#
#         menus = {
#             1: "设置",
#             99: "退出",
#         }
#
#         for key, values in menus.items():
#             print(f"{key}: {values}")
#
#         act = input(":")
#
#         match act:
#             case "1":
#                 pass
#
#             case "99":
#                 print("[bold red reverse]感谢使用")
#                 exit(0)
#
#             case _:
#                 pass

class CoreClass:
    log = None

    def __init__(self, log):
        self.log = log

    llm_api_url = ""
    llm_api_key = ""
    llm_model = ""

    def llm_config_set(self, api_url, api_key, model=None):
        """
        设置模型配置
        :param api_url: 模型提供商
        :param api_key: 模型ApiKey
        :param model: 模型名称，可以空
        :return:
        """
        self.llm_api_url = api_url
        self.llm_api_key = api_key
        if model is not None:
            self.llm_model = model
        self.log.info("大模型配置填写成功")
        self.log.info(f"当前模型提供商地址:[yellow bold reverse]{api_url}")
        self.log.info(f"当前模型:[yellow bold reverse]{'未设置' if model is None else model}")

    llm_client = None

    def llm_init(self):
        """
        初始化llm对象
        :return:
        """
        if self.llm_api_key is None or self.llm_api_key == '' or self.llm_api_url is None or self.llm_api_url == '':
            self.log.error("[red bold reverse]未初始化模型配置就调用llm_init方法")
            return
        if self.llm_client is not None:
            self.log.waring("[yellow reverse bold]正在非第一次初始化模型对象")
        self.llm_client = OpenAI(api_key=self.llm_api_key, base_url=self.llm_api_url)
        self.log.info("初始化模型对象成功")

    def llm_get_models(self, show_table=False):
        if self.llm_client is None:
            self.log.error("[red bold reverse]未初始化模型对象就调用llm_get_models方法")
            return None
        self.log.info("正在获取模型列表...")
        try:
            model_data = self.llm_client.models.list()
        except Exception as e:
            self.log.error(f"[red bold reverse]请求模型列表失败!可能是Api Key配置错误!具体消息: \n {str(e)}]")
            exit(-1)
        # self.log.info(model_data)
        if show_table:
            table = Table(
                title="模型列表",
                caption=f"当前模型提供商URL:{self.llm_api_url}",
                show_header=True,
                header_style="bold blue",
                border_style="green",
            )
            table.add_column("#", justify="right", style="cyan", no_wrap=True)
            table.add_column("模型标识符(ID)", style="magenta")
            table.add_column("模型所属组织(owned_by)", justify="center")
            table.add_column("模型名称(name)", justify="right")
            table.add_column("模型上下文总Token容量", style="dim")

            i = 0
            for model in model_data:
                table.add_row(str(i), model.id, model.owned_by, model.name, str(model.context_window))
                i += 1
            console.rule("[red bold]llm_get_models 结果")
            console.print(table)
            console.rule("[red bold]llm_get_models 结果 [reverse]END")
        data = []
        for model in model_data:
            data.append({
                "id": model.id,
                "owned_by": model.owned_by,
                "name": model.name,
                "context_window": model.context_window
            })
        return data

    def llm_config_set_model(self, model):
        """
        设置llm模型
        :param model:模型名称
        :return:
        """
        self.llm_model = model
        self.log.info(f"当前模型已切换为:[blue reverse bold]{model}")

    tools = {}

    def inject_tool(self, tool_cls):
        """
        注入工具函数
        :param tool_cls: 继承BaseTool的一个class类
        :return:
        """
        if not isinstance(tool_cls, BaseTool):
            self.log.error("[red bold reverse]传递给inject_tool方法的对象不是一个继承BaseTool的class!")
            return
        if tool_cls.tool_name in self.tools:
            self.log.error(f"[red bold reverse]当前已存在名为'{tool_cls.tool_name}'的工具!")
            return
        self.tools[tool_cls.tool_name] = tool_cls
        self.log.info(f"[green reverse]注入工具函数'{tool_cls.tool_name}'成功")

    def del_tool(self, name):
        """
        删除工具函数
        :param name:工具函数名
        :return:
        """
        if name in self.tools:
            self.tools.pop(name)
            self.log.info(f"[bold blue]删除工具函数'{name}'成功")
            return
        self.log.info(f"不存在工具函数'{name}'")

    on_chatting = False  # 表示此轮对话是否正在进行 防止同时进行多个对话 tool_call不会使对话停止
    messages = []

    def add_message(self, role, msg, show_log=False,tool_call_id = None):
        allow_roles = ['system', 'user', 'assistant', 'tool']
        if role not in allow_roles:
            self.log.error("[red bold reverse]传递的消息角色不在允许范围内")
            return
        if role == 'tool':
            if tool_call_id is None:
                self.log.error("[red bold reverse]传递了tool角色，但未传递tool_call_id!")
                exit(-1)
            self.messages.append({
                'role': role,
                'content': msg,
                'tool_call_id':tool_call_id
            })
        else:
            self.messages.append({
                'role': role,
                'content': f"Now's timestamp is  {self.get_time_stamp()}.Pls use user's language when reply user.\n {msg}"
            })
        if show_log:
            self.log.info(f"消息添加成功:\n|-角色:[blue reverse]{role}[/]\n|-内容:[green reverse]{msg}[/]")

    def get_time_stamp(self):
        """
        获取时间戳
        :return:
        """
        return int(time.time())

    has_system_msg = False

    def init_system_msg(self, msg):
        """
        初始化系统消息，用于初始化模型身份等
        :param msg: 系统消息
        :return:
        """
        if self.has_system_msg:
            self.log.error("[red bold reverse]系统消息无法二次初始化!")
            return
        self.log.info("正在初始化llm的消息列表（会清空消息列表）")
        self.messages = []
        self.add_message("system", msg)
        self.has_system_msg = True
        self.log.info("[green reverse bold]系统消息初始化成功")

    chat_rounds = 0

    def get_response(self, allow_tool_calls=False):
        """
        进行一次Chat Completions API 调用
        :param allow_tool_calls: 是否允许大模型调用tool_calls
        :return:
        """
        if not self.llm_client:
            self.log.error("[red bold reverse]未初始化模型对象时，无法调用get_response方法!")
            return
        if not self.has_system_msg:
            self.log.error("[red bold reverse]未初始化系统消息时，无法发送消息")
            return
        if not self.llm_model:
            self.log.error("[red bold reverse]未设置模型名称时，无法调用get_response方法!")
            return
        if self.messages == [] or self.messages is None:
            self.log.error("[red bold reverse]消息列表为空时，无法调用get_response方法!")
            return

        if self.on_chatting == True:
            self.log.error("[red bold reverse]当轮对话未完成，无法调用get_response方法!")
            self.log.error("[red bold reverse]欲强制停止当轮对话，请直接修改on_chatting变量为False")
            return

        self.on_chatting = True
        tools = None
        if allow_tool_calls:
            tools = []
            for tool_name, tool_cls in self.tools.items():
                build = {
                    "type": "function",
                    "function": {
                        "name": tool_cls.tool_name,
                        "description": tool_cls.tool_desc,
                        "parameters": {
                            "type": "object",
                            "properties": tool_cls.tool_properties,
                            "required": [*tool_cls.tool_properties.keys()]
                        },
                    }
                }
                tools.append(build)

        console.rule(f"[blue]第{self.chat_rounds}轮对话")
        try:
            while True:
                if self.on_chatting == False:
                    self.log.error(f"[red bold reverse]当轮对话被强制终止")
                    break

                response = self.llm_client.chat.completions.create(
                    model=self.llm_model,
                    messages=self.messages,
                    max_tokens=1024,
                    temperature=0.7,
                    stream=False,
                    tools=tools,
                )

                finish_reason = response.choices[0].finish_reason
                possible_reasons = {
                    'stop': '模型自然停止生成，或遇到stop序列中列出的字符串。',
                    'length': '输出长度达到了模型上下文长度限制，或达到了max_tokens的限制。',
                    'content_filter': '输出内容因触发过滤策略而被过滤。',
                    'tool_calls': '模型进行了工具调用。',
                    'insufficient_system_resource': '系统推理资源不足，生成被打断。',
                    'aborted': '生成过程被中断。'
                }

                if finish_reason not in possible_reasons:
                    self.log.error(f"[red bold reverse]云端返回了无法识别的结束原因，本轮对话终止。")
                    break

                content = response.choices[0].message.content
                if finish_reason == 'stop':
                    print(f"[green]{response.model} [/] > \n{content}")
                    self.add_message('assistant',content)
                elif finish_reason == 'tool_calls':
                    if allow_tool_calls:
                        tool_calls = response.choices[0].message.tool_calls
                        self.messages.append({
                            'role': 'assistant',
                            'content': None,
                            'tool_calls': tool_calls
                        })
                        for tool in tool_calls:
                            tool_id = tool.id
                            function = tool.function
                            print(f"[dim]{response.model}正在调用工具 '{function.name}'")
                            if function.name not in self.tools.keys():
                                self.log.error(f"[red bold reverse]模型正在调用工具，但此工具不存在，本轮对话终止!")
                                break
                            result = self.tools[function.name].__call__(function.arguments)
                            self.add_message('tool',result,tool_call_id=tool_id,show_log=False)
                            print(f"[dim]{response.model}工具 '{function.name}' 已调用成功")
                    else:
                        self.log.error(f"[red bold reverse]模型正在调用工具，但当前不允许，本轮对话终止!")
                        break
                else:
                    for r, t in possible_reasons.items():
                        if finish_reason == r:
                            print(f"[red bold reverse]{response.model} > {content}")

                if finish_reason != 'tool_calls':
                    break
        except Exception as e:
            self.log.error(f"[red bold reverse]请求模型回复失败!具体消息: \n {str(e)}]")
            exit(-1)

        self.on_chatting = False
        console.rule(f"[blue]第{self.chat_rounds}轮对话 [reverse]END")
        self.chat_rounds += 1


    def user_talk(self, msg):
        if not self.has_system_msg:
            self.log.error("[red bold reverse]未初始化系统消息时，无法发送用户消息")
            return
        if self.on_chatting == True:
            self.log.error("[red bold reverse]当轮对话未完成，无法调用get_response方法!")
            self.log.error("[red bold reverse]欲强制停止当轮对话，请直接修改on_chatting变量为False")
            return

        self.add_message('user',msg,show_log=False,tool_call_id=None)
        # print(f"你 > {msg}")
        self.get_response(allow_tool_calls=True)




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

if __name__ == "__main__":
    console.print(Panel.fit(
        "[bold blue]Subject Tester - AI学科水平测试[/]\n"
        "[dim]通过描述你的思维想法，免去不必要的计算，使用AI高效、快速的计算你的学科水平。[/dim]",
        border_style="red",
    ))

    # main()

    core = CoreClass(create_logger())
    core.llm_config_set("https://api.deepseek.com", os.getenv('api_key'), "deepseek-flash")
    core.llm_init()
    data = core.llm_get_models(show_table=True)
    choice = input("请输入序号以选择模型:")
    if choice != '':
        core.llm_config_set_model(data[int(choice)]['id'])
    else:
        log.warning("[reverse yellow]你没有输入，默认选择第一个模型!")
        core.llm_config_set_model(data[0]['id'])
    # core.init_system_msg("")
    # core.inject_tool()
    # i = 10
    # while i > 0:
    #     print(f"[reverse blue]【你还可以提问{i}次】")
    #     msg = input("你 > ")
    #     core.user_talk(msg)
    #     i -= 1