# baicat

把抖音「画一个故事」风格的手绘涂鸦条漫做成可复用的 Agent Skill。

## 风格特征

- **黑白线稿** + 单一红色点缀
- 手绘涂鸦感，粗糙抖动线条
- Q版简笔人物（头大身小、豆豆眼）
- 大量留白，条漫分镜式构图
- 丧系情绪，冷静自嘲

## 安装

将本目录复制到 Minis skills 目录：
```bash
cp -r baicat /var/minis/skills/
```

## 使用

对 Minis 说类似：
- "帮我画一个故事，主题是..."
- "用涂鸦条漫风格生成一组插画"
- "做个手绘漫画故事"

然后提供故事主题，Minis 会自动：
1. 写分镜脚本（6-10 格）
2. 逐格调用 GPT Image 2 生成插画
3. 组装图文故事 HTML 页面

## 文件结构

```
baicat/
├── SKILL.md                      # Skill 指令（触发后加载）
├── scripts/
│   └── generate_story.py         # 批量生图脚本
└── templates/
    └── story_page.html           # 图文故事 HTML 模板
```

## 环境变量

| 变量 | 用途 |
|------|------|
| `IMAGE_API_URL` | 生图 API 地址 |
| `OPENAI_API_KEY` | API 密钥 |

## License

MIT
