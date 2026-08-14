# baicat

双风格手绘条漫故事生成器 — Agent Skill for Minis

## 两种风格

| 中文名 | 英文名 | 描述 |
|--------|--------|------|
| **涂鸦** | doodle | 黑白线稿 + 红色点缀，Q版简笔，丧系自嘲 |
| **彩铅** | colored-pencil | 低饱和高级灰，铅笔排线，真实比例，治愈克制 |

## 使用

对 Minis 说：
- "用**涂鸦**风格画一个故事，主题是..."
- "用**彩铅**风格做个漫画故事"
- "画一个故事"（默认涂鸦风格）

## 文件结构

```
baicat/
├── SKILL.md                      # Skill 指令（双风格定义 + 工作流）
├── scripts/
│   └── generate_story.py         # 批量生图脚本（支持 --style doodle|colored-pencil）
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
