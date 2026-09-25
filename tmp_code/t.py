"""
rich 全功能演示脚本（无 Markdown 演示）
运行: python rich_demo.py
"""

import time
from rich import print as rprint
from rich.console import Console, Group
from rich.table import Table
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn,
    TaskProgressColumn, TimeRemainingColumn,
)
from rich.tree import Tree
from rich.columns import Columns
from rich.panel import Panel
from rich.syntax import Syntax
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.pretty import pprint
from rich.json import JSON
from rich.rule import Rule
from rich.align import Align
from rich.padding import Padding
from rich import inspect
from rich.traceback import install

console = Console()


# ============================================================
# 1. 富文本与样式
# ============================================================
def demo_text():
    console.rule("[bold red]1. 富文本与样式")

    rprint("Hello, [bold magenta]World[/bold magenta]! :vampire:")

    console.print("[bold]加粗[/bold] [italic]斜体[/italic] [underline]下划线[/underline] "
                  "[strike]删除线[/strike] [dim]暗淡[/dim]")

    console.print("[red]红色[/red] [on blue]蓝底[/on blue] "
                  "[bold white on red] 警告 [/bold white on red]")

    console.print("[#ff6600]橙色[/#ff6600] [rgb(100,200,255)]天蓝[/rgb(100,200,255)]")

    console.print("链接: [link=https://www.python.org]Python 官网[/link]")

    text = Text("精细控制的文本")
    text.stylize("bold underline", 0, 2)
    text.stylize("red on white", 2, 5)
    console.print(text)

    console.print(Align.center("[bold green]居中文本[/bold green]"))
    console.print(Padding("[yellow]带内边距的文本[/yellow]", (1, 4)))

    console.print(Rule("分隔线标题", style="cyan"))


# ============================================================
# 2. 表格
# ============================================================
def demo_table():
    console.rule("[bold red]2. 表格")

    table = Table(
        title="项目进度表",
        caption="数据截至今日",
        show_header=True,
        header_style="bold blue",
        border_style="green",
    )
    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("任务", style="magenta")
    table.add_column("状态", justify="center")
    table.add_column("进度", justify="right")
    table.add_column("负责人", style="dim")

    table.add_row("1", "数据采集", "[green]完成[/green]", "100%", "张三")
    table.add_row("2", "模型训练", "[yellow]进行中[/yellow]", "67%", "李四")
    table.add_row("3", "报告撰写", "[red]未开始[/red]", "0%", "王五")
    table.add_row("4", "部署上线", "[green]完成[/green]", "100%", "赵六")

    console.print(table)

    inner = Table(show_header=False, box=None)
    inner.add_row("子项 A", "[green]OK[/green]")
    inner.add_row("子项 B", "[red]FAIL[/red]")

    outer = Table(title="嵌套表格", box=None)
    outer.add_column("模块")
    outer.add_column("详情")
    outer.add_row("模块 1", inner)
    console.print(outer)


# ============================================================
# 3. 进度条与状态
# ============================================================
def demo_progress():
    console.rule("[bold red]3. 进度条与状态")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
    ) as progress:
        task1 = progress.add_task("[cyan]下载中...", total=50)
        task2 = progress.add_task("[magenta]处理中...", total=50)
        while not progress.finished:
            progress.update(task1, advance=1)
            progress.update(task2, advance=0.7)
            time.sleep(0.02)

    with console.status("[bold green]正在连接服务器...") as status:
        time.sleep(1.5)
        console.log("连接成功")


# ============================================================
# 4. 树形结构
# ============================================================
def demo_tree():
    console.rule("[bold red]4. 树形结构")

    tree = Tree("[bold yellow]项目根目录[/bold yellow]")
    src = tree.add("[blue]src/[/blue]")
    src.add("main.py")
    src.add("utils.py")
    components = src.add("[blue]components/[/blue]")
    components.add("button.py")
    components.add("table.py")

    tests = tree.add("[green]tests/[/green]")
    tests.add("test_main.py")
    tests.add("test_utils.py")

    tree.add("[dim]README.md[/dim]")
    tree.add("[dim]requirements.txt[/dim]")

    console.print(tree)


# ============================================================
# 5. 列布局
# ============================================================
def demo_columns():
    console.rule("[bold red]5. 列布局")

    console.print(Columns(["苹果", "香蕉", "橙子", "葡萄", "西瓜", "草莓"],
                          equal=True, expand=True))

    panels = [
        Panel(f"[bold]{name}[/bold]\n{desc}", title=name[:1])
        for name, desc in [
            ("Python", "简洁优雅"),
            ("Rust", "安全高效"),
            ("Go", "并发友好"),
        ]
    ]
    console.print(Columns(panels))


# ============================================================
# 6. 面板
# ============================================================
def demo_panel():
    console.rule("[bold red]6. 面板")

    console.print(Panel("这是一个基础面板", title="标题", subtitle="副标题"))

    console.print(Panel(
        "[bold red]错误[/bold red]\n系统出现异常",
        title="[red]警报[/red]",
        border_style="red",
        expand=False,
    ))

    group = Group(
        Panel("第一个面板", border_style="cyan"),
        Panel("第二个面板", border_style="magenta"),
    )
    console.print(group)


# ============================================================
# 7. 语法高亮
# ============================================================
def demo_syntax():
    console.rule("[bold red]7. 语法高亮")

    code = (
        "def fibonacci(n):\n"
        "    a, b = 0, 1\n"
        "    for _ in range(n):\n"
        "        yield a\n"
        "        a, b = b, a + b\n"
        "\n"
        "print(list(fibonacci(10)))\n"
    )
    console.print(Syntax(code, "python", line_numbers=True, theme="monokai"))


# ============================================================
# 8. 调试：log / inspect / pretty / json
# ============================================================
def demo_debug():
    console.rule("[bold red]8. 调试工具")

    console.log("这是一条日志")
    console.log("带局部变量", log_locals=True)

    inspect([1, 2, 3], methods=True, title="inspect 列表")

    data = {
        "name": "Alice",
        "age": 30,
        "skills": ["Python", "Rust", "Go"],
        "address": {"city": "Beijing", "zip": "100000"},
    }
    pprint(data, indent_guides=True)

    json_str = '{"name":"Bob","age":25,"tags":["a","b","c"],"active":true}'
    console.print(JSON(json_str))


# ============================================================
# 9. Layout 与 Live
# ============================================================
def demo_layout_live():
    console.rule("[bold red]9. Layout 与 Live")

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right"),
    )

    layout["header"].update(Panel("[bold]页头[/bold]", style="blue"))
    layout["left"].update(Panel("左侧内容", style="green"))
    layout["right"].update(Panel("右侧内容", style="magenta"))
    layout["footer"].update(Panel("[dim]页脚[/dim]", style="cyan"))

    console.print(layout)

    console.print("\n[bold]Live 动态刷新演示（3 秒）:[/bold]")
    with Live(console=console, refresh_per_second=4) as live:
        for i in range(12):
            table = Table(show_header=False)
            table.add_row("计数器", f"[bold cyan]{i}[/bold cyan]")
            table.add_row("时间", time.strftime("%H:%M:%S"))
            live.update(Panel(table, title="实时数据"))


# ============================================================
# 10. 错误回溯
# ============================================================
def demo_traceback():
    console.rule("[bold red]10. 错误回溯")

    def inner():
        x = 42
        y = 0
        return x / y

    try:
        inner()
    except Exception:
        console.print_exception(show_locals=True)


# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    install(show_locals=False)

    console.print(Panel.fit(
        "[bold yellow]Rich 全功能演示[/bold yellow]\n"
        "[dim]覆盖文本、表格、进度条、树、面板、语法高亮、调试等[/dim]",
        border_style="yellow",
    ))

    demo_text()
    demo_table()
    demo_progress()
    demo_tree()
    demo_columns()
    demo_panel()
    demo_syntax()
    demo_debug()
    demo_layout_live()
    demo_traceback()

    console.rule("[bold green]演示结束")
    console.print("[bold green]所有功能演示完毕！[/bold green] :tada:")