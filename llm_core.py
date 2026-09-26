import shutil
import time
from rich.table import Table
from rich.console import Console
from rich import traceback
from rich import print
from openai import OpenAI
from dotenv import load_dotenv
from tools.BaseTool import BaseTool
import logging
from rich.logging import RichHandler

# 加载 .env 文件
load_dotenv()
traceback.install(show_locals=True)
MAX_WIDTH = 100
console = Console(width=min(MAX_WIDTH, shutil.get_terminal_size().columns))

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(markup=True)]
)
log = logging.getLogger(__name__)

class LLMCoreClass:
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

    def add_message(self, role, msg, show_log=False, tool_call_id=None):
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
                'tool_call_id': tool_call_id
            })
        else:
            self.messages.append({
                'role': role,
                'content': msg
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
        self.add_message("system",
                         f"Now's timestamp is  {self.get_time_stamp()}.Pls use user's language when reply user.\n{msg}")
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
                    max_tokens=393216,
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
                    self.add_message('assistant', content)
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
                            self.add_message('tool', result, tool_call_id=tool_id, show_log=False)
                            print(f"[dim]{response.model}工具 '{function.name}' 已调用成功")
                    else:
                        self.log.error(f"[red bold reverse]模型正在调用工具，但当前不允许，本轮对话终止!")
                        break
                else:
                    for r, t in possible_reasons.items():
                        if finish_reason == r:
                            print(f"[red bold reverse]{response.model} > {t}")

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

        self.add_message('user', msg, show_log=False, tool_call_id=None)
        # print(f"你 > {msg}")
        self.get_response(allow_tool_calls=True)