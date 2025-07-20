from feedgen.feed import FeedGenerator
from datetime import datetime, timezone, timedelta
from flask import url_for
import markdown

# 设置中国时区
CHINA_TZ = timezone(timedelta(hours=8))

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
            fe.description(markdown.markdown(post.content))
            # 确保时间戳包含UTC时区信息
            fe.pubDate(post.created_at.replace(tzinfo=CHINA_TZ) if post.created_at.tzinfo is None else post.created_at)
            fe.updated(post.updated_at.replace(tzinfo=timezone.utc) if post.updated_at.tzinfo is None else post.updated_at)
            
            # 添加标签
            for tag in post.tags:
                fe.category(term=tag.name)
    
    return fg.rss_str(pretty=True)