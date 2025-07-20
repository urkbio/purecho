from datetime import datetime
from xml.etree import ElementTree as ET
from models import Post

def generate_sitemap(posts, config):
    # 创建根元素
    urlset = ET.Element('urlset', {'xmlns': 'http://www.sitemaps.org/schemas/sitemap/0.9'})
    
    # 添加首页
    home_url = ET.SubElement(urlset, 'url')
    ET.SubElement(home_url, 'loc').text = config.SITE_URL
    ET.SubElement(home_url, 'lastmod').text = datetime.now().strftime('%Y-%m-%d')
    ET.SubElement(home_url, 'changefreq').text = 'daily'
    ET.SubElement(home_url, 'priority').text = '1.0'
    
    # 添加所有文章和页面
    for post in posts:
        url = ET.SubElement(urlset, 'url')
        if post.is_page:
            ET.SubElement(url, 'loc').text = f'{config.SITE_URL}/page/{post.slug}'
        else:
            ET.SubElement(url, 'loc').text = f'{config.SITE_URL}/post/{post.slug}'
        ET.SubElement(url, 'lastmod').text = post.updated_at.strftime('%Y-%m-%d')
        ET.SubElement(url, 'changefreq').text = 'weekly'
        ET.SubElement(url, 'priority').text = '0.8'
    
    # 生成XML
    tree = ET.ElementTree(urlset)
    ET.indent(tree, space='  ')
    return ET.tostring(urlset, encoding='unicode', method='xml')