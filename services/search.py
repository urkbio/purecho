import re
from html import unescape

import nh3

from services.markdown import render_html

TITLE_WEIGHT = 0.7
CONTENT_WEIGHT = 0.3
EXCERPT_LENGTH = 160
EXCERPT_CONTEXT = 60


def _compile_query(query):
    # re.escape 确保用户输入只按字面匹配，不会被当作正则表达式执行。
    return re.compile(re.escape(query), re.IGNORECASE)


def _plain_text(content):
    html = render_html(content)
    text = nh3.clean(html, tags=set())
    return ' '.join(unescape(text).split())


def _highlight_segments(text, pattern):
    segments = []
    end = 0

    for match in pattern.finditer(text):
        if match.start() > end:
            segments.append((text[end:match.start()], False))
        segments.append((match.group(), True))
        end = match.end()

    if end < len(text):
        segments.append((text[end:], False))

    return segments or [(text, False)]


def _excerpt_segments(text, pattern):
    match = pattern.search(text)
    if not match:
        return []

    start = max(0, match.start() - EXCERPT_CONTEXT)
    end = min(len(text), max(match.end(), start + EXCERPT_LENGTH))
    if end - start < EXCERPT_LENGTH:
        start = max(0, end - EXCERPT_LENGTH)

    excerpt = text[start:end]
    if start > 0:
        excerpt = '…' + excerpt
    if end < len(text):
        excerpt += '…'

    return _highlight_segments(excerpt, pattern)


def search_posts(posts, query):
    """按标题 0.7、正文 0.3 的权重搜索文章，同分时保持原有顺序。"""
    query = query.strip()
    if not query:
        return []

    pattern = _compile_query(query)
    results = []

    for post in posts:
        content = _plain_text(post.content)
        title_match = pattern.search(post.title)
        content_match = pattern.search(content)
        score = (
            (TITLE_WEIGHT if title_match else 0)
            + (CONTENT_WEIGHT if content_match else 0)
        )

        if not score:
            continue

        results.append({
            'post': post,
            'score': score,
            'title_segments': (
                _highlight_segments(post.title, pattern)
                if title_match else [(post.title, False)]
            ),
            'excerpt_segments': (
                _excerpt_segments(content, pattern)
                if content_match else []
            ),
        })

    # Python 排序稳定，因此同分结果会保留路由传入的时间排序。
    results.sort(key=lambda result: result['score'], reverse=True)
    return results
