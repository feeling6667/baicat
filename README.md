# baicat

> 一个**手绘涂鸦条漫故事生成器** Agent Skill。给一个故事主题，自动拆分镜、批量出图、拼装成可浏览的 HTML 图文故事页。两种风格：黑白涂鸦（丧系自嘲）与彩铅治愈（低饱和克制）。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 这是什么

抖音上"画一个故事"风格的手绘条漫很受欢迎，但每次都要手动拆分镜、逐张生图、再排版拼页，流程碎且重复。

baicat 把这套流程沉淀成一个可复用的 Skill：**你只管给故事主题，baicat 负责剩下的全部**——

- 把主题拆成 6–10 格条漫分镜，每格配画面描述和短文案；
- 设计情绪线（从一个状态渐变到另一个，如 期待→麻木→释然）；
- 逐格调用 GPT Image 2 批量出图，画风配方驱动、多格一致；
- 用 HTML 模板自动拼装成独立可浏览的故事页。

**它直接产出图文成品**，不只是一段提示词。

## 两种风格

| 中文名 | 英文名 | 调性 | 触发词 |
|--------|--------|------|--------|
| **涂鸦** | `doodle` | 黑白线稿 + 唯一红色点缀，Q版简笔，丧系自嘲，上方留白填手写文字 | 涂鸦、黑白涂鸦、丧系涂鸦 |
| **彩铅** | `colored-pencil` | 低饱和高级灰，铅笔排线，真实比例，治愈克制 | 彩铅、彩色铅笔、治愈条漫 |

不指定风格时默认「涂鸦」。

| | |
|:---:|:---:|
| <img src="examples/style-doodle.png" width="300"><br>**涂鸦** doodle<br>黑白线稿 + 红色点缀，Q版简笔 | <img src="examples/style-colored-pencil.png" width="300"><br>**彩铅** colored-pencil<br>低饱和高级灰，铅笔排线，治愈克制 |

## 工作流

### 1. 确认风格

用户说"涂鸦"→ 风格 A；用户说"彩铅"→ 风格 B；未指定 → 询问或默认涂鸦。

### 2. 写故事脚本

将用户主题拆成 6–10 格条漫分镜，每格包含：
- **画面**：一句话描述场景动作（英文，填入配方的 SCENE）
- **文案**：短句（≤15字），涂鸦风格放图下，彩铅风格写在画面上

情绪线设计：从一个状态渐变到另一个状态（如：期待→麻木→释然）。

### 3. 批量生成图片

```bash
python3 scripts/generate_story.py \
  --story-json story.json \
  --output-dir ./output \
  --style doodle
```

故事 JSON 格式：
```json
{
  "title": "等",
  "style": "doodle",
  "anchor": "optional/path/anchor.png",
  "panels": [
    {"id": "p1", "scene": "A girl sitting on a chair hugging knees, quietly waiting. Red hair clip. Phone on table."},
    {"id": "p2", "scene": "Same pose, calendar page flipped, sky dimmer."}
  ]
}
```

脚本从 `STYLES.md` 读取对应画风的配方代码块，自动填充 `【主体】` 占位符，逐格调用 GPT Image 2，保存为 `story_p1.jpeg` 等。

### 4. 组装图文故事页面

用 `templates/story_page.html` 模板生成最终 HTML 页面：
- 替换 `{{TITLE}}` 为故事标题
- 复制 panel 块，替换图片文件名和文案
- 涂鸦风格：红色文案用 `<span class="red">` 包裹，文案在图下
- 彩铅风格：文案直接写在图上方区域，用手写体 CSS

## 用法示例

对 AI Agent 说：

```
用涂鸦风格画一个故事，主题是"等一个人"
```

```
用彩铅风格做个漫画故事，讲深夜加班回家路上的心情
```

```
画一个故事（默认涂鸦风格）
```

### 列出可用画风

```bash
python3 scripts/generate_story.py --list-styles
# Available styles in STYLES.md:
#   - doodle
#   - colored-pencil
```

## 配方驱动 & 画风一致性

### 配方驱动

画风 prompt 存在 `STYLES.md` 配方库中，脚本只负责提取配方 + 填充占位符，**禁止手工缩写或同义改写**。新增画风只需在 `STYLES.md` 加一段配方，不改脚本代码：

```markdown
## my-new-style 我的风格

```
这里是该画风的完整 prompt 模板。
SCENE: 【主体】
```
```

### 画风锚点（多格一致性）

连续分镜的画风一致性是条漫的核心难题。baicat 支持 **anchor 锚点图机制**：

- 故事 JSON 可选 `anchor` 字段，指定一张画风锚点图；
- 设定后每格生成都把它作为 style-only 参考传入，锁定多格画风一致（只继承线条/配色/比例/氛围，不复制人物服装站位）；
- 未指定 anchor 时，第 2 格起自动用上一格输出作为参考，保证连贯。

```json
{
  "title": "深夜归途",
  "style": "colored-pencil",
  "anchor": "examples/style-colored-pencil.png",
  "panels": [...]
}
```

## 环境变量

| 变量 | 用途 |
|------|------|
| `IMAGE_API_URL` | 生图 API 地址（如 `https://host/v1`） |
| `OPENAI_API_KEY` | API 密钥 |

## 目录结构

```
baicat/
├── README.md                      # 本文件
├── SKILL.md                       # Skill 指令（风格定义 + 工作流 + 约束）
├── STYLES.md                      # 画风配方库（配方驱动，加画风只改这里）
├── LICENSE
├── scripts/
│   └── generate_story.py          # 配方驱动批量生图脚本
├── templates/
│   └── story_page.html            # 图文故事 HTML 模板
└── examples/
    ├── style-doodle.png           # 涂鸦风格示例
    └── style-colored-pencil.png   # 彩铅风格示例
```

## 接入方式

### Minis / Claude Code / 任意支持 SKILL.md 的 Agent

```bash
git clone https://github.com/feeling6667/baicat.git
```

把仓库放到 skills 目录（如 `/var/minis/skills/baicat/`），Agent 会自动识别 `SKILL.md` 并在用户说"画一个故事"时触发。

### 其他工具

把 `SKILL.md` 的内容粘进系统提示词 / 规则文件，把 `scripts/` 和 `templates/` 拷进项目即可。

## 设计原则

- **直接产出图文成品**——不只是提示词，而是从故事到可浏览 HTML 页面的端到端链路。
- **配方驱动**——画风 prompt 存 `STYLES.md`，脚本只提取不缩写，保证画风不漂移。
- **多格一致**——anchor 锚点图机制锁定连续分镜的画风统一。
- **留白为主**——不要把画面填满，给情绪留呼吸空间。
- **涂鸦上方留白填字、彩铅文字入画**——两种风格都支持图中文字，但布局不同：涂鸦在上三分之一留白区填手写中文，彩铅文字融入画面氛围。

## License

[MIT](LICENSE) © feeling6667
