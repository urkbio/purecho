import pyromark


_OPTIONS = (
    pyromark.Options.ENABLE_TABLES
    | pyromark.Options.ENABLE_STRIKETHROUGH
)


def _convert_soft_breaks(text):
    # PyroMark 没有 nl2br 选项，利用事件提供的字节位置添加硬换行标记。
    positions = [
        span['start']
        for event, span in pyromark.events_with_range(text, options=_OPTIONS)
        if event == 'SoftBreak'
    ]
    source = text.encode('utf-8')
    for position in reversed(positions):
        source = source[:position] + b'\\' + source[position:]
    return source.decode('utf-8')


def render_html(text):
    return pyromark.html(_convert_soft_breaks(text), options=_OPTIONS)
