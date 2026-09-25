import logging
from rich.logging import RichHandler

logging.basicConfig(
    level="NOTSET",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(markup=True)]
)

log = logging.getLogger("rich")
log.info("Hello, World!")
log.info("Hello, World!")
log.info("Hello, World!")
log.info("Hello, World!")
log.info("Hello, World!")
log.info("Hello, World!")
log.info("Hello, World!")
log.info("Hello, World!")
log.info("Hello, World!")
log.error("GET [bold red reverse]TIMEOUT")
log.info("[italic]Hello, World!")

"""
粗体	[bold] [b]	加粗文本
斜体	[italic] [i]	斜体文本
下划线	[underline] [u]	添加下划线
删除线	[strike] [s]	添加删除线
暗淡	[dim]	降低文本亮度
闪烁	[blink]	文本闪烁（终端支持时）
反转	[reverse]	前景色与背景色互换
隐藏	[conceal]	隐藏文本（部分终端）
颜色	[red] [green] [blue]	标准颜色名，也支持 [bright_blue] 等
背景色	[on blue]	设置背景颜色
"""
