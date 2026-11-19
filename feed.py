from feedgen.feed import FeedGenerator
from datetime import datetime, timezone, timedelta
from flask import url_for
import nh3

from services.markdown import render_html

# 设置中国时区
CHINA_TZ = timezone(timedelta(hours=8))

def render_markdown(text):
    html = render_html(text)

    return nh3.clean(
        html,
        tags={
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'p', 'br', 'hr', 'blockquote',
            'strong', 'em', 'del',
            'ul', 'ol', 'li',
            'pre', 'code',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'a', 'img'
        },
        attributes={
            'a': {'href', 'title'},
            'img': {'src', 'alt', 'title'}
        },
        url_schemes={'http', 'https', 'mailto'}
    )

def generate_feed(posts, config):
    fg = FeedGenerator()
    fg.title(config.SITE_TITLE)
    fg.description(config.SITE_DESCRIPTION)
    fg.link(href=config.SITE_URL)
    fg.language('zh-CN')
    
    for post in posts:
        if not post.is_page:  # 只为文章生成RSS，不包含独立页面
            fe = fg.add_entry()
            fe.title(post.title)
            fe.link(href=f"{config.SITE_URL}{url_for('post', slug=post.slug)}")

            # 处理 markdown（支持 ``` 代码块）
            html = render_markdown(post.content)

            # 使用 content:encoded，保证代码块正常显示
            fe.content(html, type='CDATA')

            fe.pubDate(
                post.created_at.replace(tzinfo=CHINA_TZ)
                if post.created_at.tzinfo is None
                else post.created_at
            )
            fe.updated(
                post.updated_at.replace(tzinfo=timezone.utc)
                if post.updated_at.tzinfo is None
                else post.updated_at
            )

            # 添加标签
            for tag in post.tags:
                fe.category(term=tag.name)

    return fg.rss_str(pretty=True)