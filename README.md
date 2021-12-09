# NotionToGithubBlog

自动化拉取Notion Database中的文章，转化为markdown

可以用于 Notion 到 Hugo/Hexo 等静态博客的自动化发布

是否有这样的烦恼：在notion中写了一篇笔记或文章，想要发布到github静态博客上，发现需要先将文章转化成markdown，图片需要上传到图床，然后贴入markdown，然后再推送到github，等待action自动构建静态博客

这个action旨在部分自动化这个流程（全部自动化需要配合其他的action和操作）

只需要在 notion 中建立一个用于博客发布的 database，然后写完笔记后填入这个 database，再使用一些手段触发 CI 即可完成博客文章的发布

如果把你的静态博客比作一个cms，那么这个 notion database 就是 cms 的内容管理后端（目前只支持增加和更新文章）

要使用该action，首先你需要在 notion 中创建一个 database，这个database需要有几个字段，字段名如下:

- Name (title): 文章标题
- Article (text): 文章链接
- MDFilename (text): 创建的 markdown 文件名
- Category (select): 文章分类
- Tags (multi_select): 文章标签
- IsPublish (checkbox): 文章是否发布
- NeedUpdate (checkbox): 文章是否有更新
- CreateAt (Created time): 创建时间
- UpdateAt (Last edited time): 更新时间

样例如下

![](img/20211209161749.jpg)