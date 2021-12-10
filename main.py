import os
from notion_client import Client
from notiontomd import NotionToMarkdown
import re
from github import Github
import hashlib
import time
import base64
from urllib.parse import urlparse
import requests
import yaml
import logging

logger=logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter=logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger.addHandler(logging.StreamHandler())

class Notion:
    def __init__(self, token, database_id):
        self.notion = Client(auth=token)
        self.database_id = database_id
    
    def get_page_id(self, data: dict) -> list:
        rich_text_node = data['properties'].get('Article', {})
        mentions = []
        if rich_text_node['type'] != 'rich_text':
            raise TypeError("this field is not a rich text")
        for i in rich_text_node['rich_text']:
            if i['type'] == 'mention':
                mentions.append(i['mention']['page']['id'])
        return mentions[0] if len(mentions) > 0 else None
    
    def title(self, data: dict) -> str:
        title_node = data['properties'].get('Name', {})
        title = ''
        if title_node['type'] != 'title':
            raise TypeError("this field is not a title")
        for i in title_node['title']:
            title += i['plain_text']
        return title
    
    def is_publish(self, data: dict) -> bool:
        return data['properties'].get('IsPublish', {}).get('checkbox', False)

    def need_update(self, data: dict) -> bool:
        return data['properties'].get('NeedUpdate', {}).get('checkbox', False)
    
    def md_filename(self, data: dict) -> str:
        rich_text_node = data['properties'].get('MDFilename', {})
        file_name = ''
        if rich_text_node['type'] != 'rich_text':
            raise TypeError("this field is not a rich text")
        for i in rich_text_node['rich_text']:
            file_name += i['plain_text']
        return file_name
    
    def category(self, data: dict) -> list:
        return data['properties'].get('Category', {}).get('select', {}).get('name', '')
    
    def tags(self, data: dict) -> list:
        tags_ = []
        tags_node = data['properties'].get('Tags', {}).get('multi_select', [])
        for i in tags_node:
            tags_.append(i['name'])
        return tags_
    
    def create_at(self, data: dict) -> str:
        return data['properties'].get('CreateAt', {}).get('created_time', '')

    def update_at(self, data: dict) -> str:
        return data['properties'].get('UpdateAt', {}).get('last_edited_time', '')
    
    def publish(self, data: dict) -> bool:
        page_id = data['id']
        self.notion.pages.update(page_id, properties={
            "IsPublish": { "checkbox": True },
            "NeedUpdate": { "checkbox": False }
        })

    def items_changed(self):
        '''获取需要更改的项'''
        data = self.notion.databases.query(database_id=self.database_id, filter={
            "or": [
                {
                    "property": "IsPublish",
                    "checkbox": {
                        "equals": False,
                    },
                },
                {
                    "property": "NeedUpdate",
                    "checkbox": {
                        "equals": True,
                    },
                },
            ]
        })
        return data.get('results') or []

class ImgStore:
    def __init__(self, img_data, img_ext, **kwargs):
        self.img_ext = img_ext
        self.img_data = img_data
        self.kwargs = kwargs
    
    def get_md5(self) -> str:
        md5hash = hashlib.md5(self.img_data)
        return md5hash.hexdigest()

    def store(self):
        raise NotImplementedError

class ImgStoreRemoteGithub(ImgStore):
    '''将图片上传到github图床'''
    def get_store_path(self, path) -> str:
        md5str = self.get_md5()
        return os.path.join(path, f'{md5str[:2]}/{md5str[2:4]}/{md5str}{self.img_ext}').replace('\\', '/')

    def store(self):
        github_token = self.kwargs['github_token']
        repo = self.kwargs['repo']
        store_path_prefix = self.kwargs['store_path_prefix']
        branch = self.kwargs['branch']
        gh = Github(github_token)
        gh_repo = gh.get_repo(repo)
        store_path = self.get_store_path(store_path_prefix)
        gh_repo.create_file(
            path=store_path,
            message=f'notion img auto upload at {time.strftime("%Y-%m-%d %H:%M:%S")}',
            content=base64.b64encode(self.img_data),
            branch=branch
        )
        return f'https://raw.githubusercontent.com/{repo}/{branch}/{store_path}'

class ImgStoreLocal(ImgStore):
    '''将图片保存在仓库内'''
    def get_img_filename(self):
        md5str = self.get_md5()
        return f'{md5str}{self.img_ext}'

    def get_img_path(self, path) -> str:
        return os.path.join(path, self.get_img_filename())
    
    def sotre(self):
        store_path_prefix = self.kwargs['store_path_prefix']
        url_path_prefix = self.kwargs['url_path_prefix']
        if not os.path.exists(store_path_prefix):
            os.makedirs(store_path_prefix)
        store_path = self.get_img_path(self, store_path_prefix)
        with open(store_path, 'rw+') as f:
            f.write(self.img_data)
        return self.get_img_path(self, url_path_prefix)

class ImgHandler:
    '''图片处理
    
    Attributes:
        markdown_text: markdown文本
        img_store_type： img储存类型：local, github
    '''
    pattern = re.compile(r'(!\[[^\]]*\]\((.*?)\s*("(?:.*[^"])")?\s*\))')

    def __init__(self, markdown_text, img_store_type, **kwargs):
        self.markdown_text = markdown_text
        self.kwargs = kwargs
        self.img_handler_cls = None
        if img_store_type == 'local':
            self.img_handler_cls = ImgStoreLocal
        elif img_store_type == 'github':
            self.img_handler_cls = ImgStoreRemoteGithub
    
    def get_ext_from_imglink(self, imglink):
        url_path = urlparse(imglink).path
        return os.path.splitext(url_path)[1]
    
    def get_img_data_from_url(self, url):
        return requests.get(url).content

    def extract_n_replace_imglink(self) -> str:
        self.pattern.
        for item in self.pattern.findall(self.markdown_text):
            match_text = item[0]
            imglink = item[1]
            img_ext = self.get_ext_from_imglink(imglink)
            img_data = self.get_img_data_from_url(imglink)
            new_imglink = self.img_handler_cls(img_data, img_ext, **self.kwargs).store()
            img_text = match_text.replace(imglink, new_imglink)
            self.markdown_text = self.markdown_text.replace(match_text, img_text)
        return self.markdown_text

def get_markdown_with_yaml_header(page_node: dict, article_content: str, notion: Notion):
    yaml_header = {
        'title': notion.title(page_node),
        'date': notion.create_at(page_node),
        'showToc': True,
        'tags': notion.tags(page_node),
        'categories': notion.category(page_node),
    }
    header_text = yaml.dump(yaml_header)
    return f'---\n{header_text}\n---\n\n\n\n{article_content}'

def save_markdown_file(path_prefix: str, content: str, filename: str):
    logger.info(f'save markdwon file to {os.path.join(os.path.dirname(os.path.abspath(__file__)), path_prefix, filename)}')
    if not os.path.exists(path_prefix):
        os.makedirs(path_prefix)
    md_filepath = os.path.join(path_prefix, filename)
    with open(md_filepath, 'w+', encoding='utf-8') as f:
        f.write(content)

def github_action_env(key):
    return f'INPUT_{key}'.upper()

def main():
    notion_token = os.environ[github_action_env('NOTION_TOKEN')]
    notion_database_id = os.environ[github_action_env('NOTION_DATABASE_ID')]
    img_store_type = os.getenv(github_action_env('IMG_STORE_TYPE')) or 'local' # 可选 local, github
    img_store_path_prefix = os.getenv(github_action_env('IMG_STORE_PATH_PREFIX')) or 'static/notionimg'
    img_store_url_path_prefix = os.getenv(github_action_env('IMG_STORE_URL_PATH_PREFIX')) or '/notionimg/'
    img_store_github_token = os.getenv(github_action_env('IMG_STORE_GITHUB_TOKEN'))
    img_store_github_repo = os.getenv(github_action_env('IMG_STORE_GITHUB_REPO'))
    img_store_github_branch = os.getenv(github_action_env('IMG_STORE_GITHUB_BRANCH'))
    md_store_path_prefix = os.getenv(github_action_env('MD_STORE_PATH_PREFIX')) or 'content/posts' # 保存markdown文件的目录

    notion = Notion(notion_token, notion_database_id)
    for page_node in notion.items_changed():
        logger.info(f'get page content from notion...')
        page_id = notion.get_page_id(page_node)
        # 将page转化为markdown
        logger.info(f'parse <<{notion.title(page_node)}>>...')
        markdown_text = NotionToMarkdown(notion_token, page_id).parse()
        # 提取markdown内的图片，放入自己的图床替换链接
        logger.info(f'replace img link in article <<{notion.title(page_node)}>>...')
        img_store_kwargs = {
            'github_token': img_store_github_token,
            'repo': img_store_github_repo,
            'store_path_prefix': img_store_path_prefix,
            'branch': img_store_github_branch,
            'url_path_prefix': img_store_url_path_prefix,
        }
        img_handler = ImgHandler(markdown_text, img_store_type, **img_store_kwargs)
        markdown_text = img_handler.extract_n_replace_imglink()
        # 生成yaml标头的markdown供hugo生成
        logger.info(f'generate and save article <<{notion.title(page_node)}>>...')
        markdown_with_header = get_markdown_with_yaml_header(page_node, markdown_text, notion)
        # 保存markdown到指定目录
        save_markdown_file(md_store_path_prefix, markdown_with_header, notion.md_filename(page_node))
        # 更新notion中的对应项
        logger.info('update page property for article <<{notion.title(page_node)}>>...')
        notion.publish(page_node)
        logger.info('all done!!!')

if __name__ == '__main__':
    main()