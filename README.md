# baicat

> **抖音图文故事智能生产系统（V3）**。从素材筛选到发布全链路：七条淘汰线机械过筛（不打分，AI 只生产执行，判断权在规则/用户/数据三处）→ 三候选钩子博主挑选 → 人物/场景/道具一致性分镜 → 生图（路线自适应：先模型自带生图，再 API 直调，兜底导出提示词）→ 四层 QA → 标题三件套+评论设计 → 内容指纹登记反哺。生图默认**彩铅**，明确说"涂鸦"才切黑白丧系。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 这是什么

抖音上"画一个故事"风格的手绘条漫很受欢迎，但每次都要手动拆故事、反复纠结结局、再逐张生图排版，流程碎且重复。更痛的是：**不知道一个故事值不值得做**，以及做着做着**自己重复自己**（换皮故事）。

baicat V3 把整个内容生产链沉淀成一个 Skill，**AI 不当裁判**（不打分不评级，机械判定交给脚本，品味判断交给你，客观分交给发布数据）：

```
素材 → 【确认点①】七条淘汰线+指纹查重 → 【确认点②】3候选钩子你挑+结局
→ 【确认点③】人物卡/场景道具锁定+分镜 → 【确认点④】生图+四层QA
→ 【确认点⑤】标题三件套+评论问题+登记 → 发布 → 数据回流反哺选题
```

双运行模式：**导演模式**五个确认点逐步确认；**批量模式**②③④全自动，一次囤多篇。

## 两种风格

| 中文名 | 英文名 | 调性 | 触发 |
|--------|--------|------|------|
| **彩铅（默认）** | `colored-pencil` | 低饱和高级灰，铅笔排线，真实比例，治愈克制 | 默认；或说"彩铅/彩色铅笔/治愈条漫" |
| **涂鸦** | `doodle` | 黑白线稿 + 唯一红色点缀，Q版简笔，丧系自嘲 | 明确强调"涂鸦/黑白涂鸦/丧系涂鸦" |

**默认彩铅直接出图**；只有明确强调"涂鸦"才切涂鸦。

| | |
|:---:|:---:|
| <img src="examples/style-colored-pencil.png" width="300"><br>**彩铅** colored-pencil<br>低饱和高级灰，铅笔排线，治愈克制 | <img src="examples/style-doodle.png" width="300"><br>**涂鸦** doodle<br>黑白线稿 + 红色点缀，Q版简笔 |

## 工作流（五确认点）

> 每个确认点停下等用户拍板；确认点④ QA 全过时不停留直接进⑤。

1. **确认点① 素材筛选**：七条淘汰线逐条过（每条给证据）+ 内容指纹查重 + 30 篇限额检查。规则见 `references/选题淘汰规则.md`。
2. **确认点② 钩子+结局**：3 个候选钩子（异常事件/反常行为/结果先行）由博主挑 + 信息缺口三字段 + 结局五选一推荐。规则见 `references/抖音钩子规则.md`。
3. **确认点③ 资产+分镜**：人物卡（`{{角色名}}` 占位符，单故事内统一）+ 场景/道具锁定 + 视觉基调（光影#N/画纸#N）+ 逐格分镜（黄金前3格 + 无效镜头检测）。
4. **确认点④ 生图+QA**：跑脚本生图 → `story_qa.py` 四层 pass/fail 检查单（AI 亲自逐张看图查人物一致性）→ fail 必改复检。
5. **确认点⑤ 发布包**：标题三件套 + 评论问题（四类轮换）+ 登记 `content_registry`。

发布后数据回填 → `content_registry.py stats` 输出组合分析反哺下批选题。

## 快速开始

对 AI Agent 说：

```
帮我做个故事：深夜公司只剩我和保洁阿姨，她递给我一杯热水
```

```
从这几个素材里筛选值得做的，批量出 3 个成品
```

**确认点④ 生图命令**（路线自适应，详见 SKILL.md）：

```bash
python3 scripts/generate_story.py \
  --story-json story.json \
  --output-dir ./output \
  --image-route auto   # auto=先模型自带生图(minis-model-use)，没有再 API；可强制 model/api
```

**QA 检查单**：

```bash
python3 scripts/story_qa.py --template > qa_result.json   # 导出模板，AI 填写
python3 scripts/story_qa.py --input qa_result.json        # 汇总，fail 出必改清单
```

**内容指纹/限额/统计**：

```bash
python3 scripts/content_registry.py --registry data/content_registry.json check --file dims.json
python3 scripts/content_registry.py --registry data/content_registry.json register --file work.json
python3 scripts/content_registry.py --registry data/content_registry.json stats --last 20 --with-metrics
```

故事 JSON 格式：
```json
{
  "title": "等",
  "style": "colored-pencil",
  "lighting": 3,
  "paper": 1,
  "split2": true,
  "anchor": "optional/path/anchor.png",
  "characters": {
    "主角": "25-year-old Chinese office worker, shoulder-length straight black hair...",
    "配角": "50-year-old cleaning lady..."
  },
  "panels": [
    {"id": "p1", "scene": "{{主角}} sitting on a chair hugging knees, quietly waiting.", "text": "等一个人。"}
  ]
}
```

- `lighting`（1-6）/ `paper`（1-5）：确认点③已锁定；不填由脚本按情绪自动推断 / 跨篇轮换（抗同质化）。
- `characters`：**人物外貌描述字典**，保证单故事内角色统一。scene 里用 `{{角色名}}` 占位符，生成时自动替换成完整外貌。
- `split2`：彩铅且总格数>6 时，第1格作封面单图，其余两两拼成 3:4 双分镜（极淡浅灰细线，禁粗黑边框）。
- `multipanel`（配 `"multipanel_cover": false`、`"multipanel_style": "free|regular"`）：整页多格模式，
  一张 3:4 图装 3-5 格，超 5 格自动拆页。
- `page_native`（配 multipanel）：**整页原生生图**——不逐格生成拼接，把全页 scene 合并成
  PAGE LAYOUT 描述，一次调用 GPT 画出整页（上大格+中排小格+下大格、白边留白分隔）。
  产物只有 `story_page_<n>.jpeg`，无分镜单元。拼接版有扁长格裁切风险，长镜头故事推荐 page_native。
- `anchor`：画风锚点图，锁多格画风一致；不填则第2格起用上一格输出参考。
- `text`：两风格生图均**不画字**，仅作后期加字依据 + 彩铅光影情绪推断，生图只留顶部约1/3大留白区。
- `text_in_image`：可选（或 CLI `--text-in-image`），生图直接把 `text` 一行手写楷体（带笔锋）画进顶部留白区；开启后无需 letter_baicat 加字（auto 自动跳过），整页多格路线不支持。
- `--export-prompts`：**不生图、零 API 成本**，把整套生图提示词（与脚本实际发送的完全一致）导出成可复制的 Markdown 文档（默认 `<output-dir>/生图提示词.md`），供拿去其他 agent 出图；文档含整篇统一的光影/画纸锁定值、每图的画面/旁白/尺寸/建议文件名与整块提示词。

## 抗同质化（双层）

- **视觉层**：光影 6 套 + 画纸 5 套变量（存 `STYLES.md`），同一篇锁一套、跨篇轮换，组合记录进 `USAGE.json`；出图后用醒图做人工痕迹二次加工（`references/抗同质化手工流程.md`）。
- **内容层（V3）**：8 维内容指纹（人物关系×主题×冲突×钩子×结局×情绪×场景×道具）查重 + 30 篇限额保护，杜绝"换皮故事"（`references/选题淘汰规则.md`）。

## 配方驱动 & 画风一致性

- **配方驱动**：画风 prompt 存 `STYLES.md`，脚本只提取配方 + 填占位符，禁止手工缩写或同义改写。新增画风只需在 `STYLES.md` 加一段配方。
- **多格一致**：`anchor` 锚点图机制锁定连续分镜画风统一；未指定时第2格起用上一格输出作参考。
- **人物一致（V2.4+）**：`characters` 字段 + `{{角色名}}` 占位符，单故事内角色外貌统一。

## 生图路线（V3 自适应）

skill 可跑在不同 agent 环境，`generate_story.py --image-route` 按优先级自动探测：

1. **模型自带生图**（最优先）：环境有 `minis-model-use` 即用（GPT Image 2）
2. **API 直调**：走 `IMAGE_API_URL` + `OPENAI_API_KEY`
3. **导出提示词**（兜底）：`--export-prompts` 出提示词文档，拿去其他有生图能力的 agent，出完放回输出目录再跑脚本自动拼接/加字

## 环境变量

| 变量 | 用途 |
|------|------|
| `IMAGE_API_URL` | 生图 API 地址（如 `https://host/v1`，API 路线用） |
| `OPENAI_API_KEY` | API 密钥（API 路线用） |

两条路线都不可用时，`--export-prompts` 永远可用（零成本导出提示词）。

## 目录结构

```
baicat/
├── README.md                      # 本文件
├── SKILL.md                       # Skill 指令（五确认点流程 + 风格定义 + 生成工作流 + 约束）
├── STYLES.md                      # 画风配方库 + 光影/画纸变量库（加画风只改这里）
├── LICENSE
├── scripts/
│   ├── generate_story.py          # 配方驱动批量生图（lighting/paper/split2/multipanel/路线自适应）
│   ├── letter_baicat.py           # 确定性加字（--auto 批量）
│   ├── multipanel_layouts.py      # 整页多格布局模板
│   ├── content_registry.py        # V3 内容数据库（指纹/限额/登记/统计）
│   └── story_qa.py                # V3 四层 QA 检查单执行器
├── data/
│   └── content_registry.json      # V3 账号历史作品数据库
├── templates/
│   └── story_page.html            # 图文故事 HTML 模板
├── references/
│   ├── 选题淘汰规则.md             # V3 七条淘汰线判定标准
│   ├── 抖音钩子规则.md             # V3 三类钩子 + 信息缺口机制
│   ├── 抗同质化手工流程.md          # 醒图二次加工 SOP
│   ├── 数据复盘表.md               # 发布数据复盘 + V3 反哺闭环
│   └── lettering-manifest.example.json
└── examples/
    ├── style-colored-pencil.png
    └── style-doodle.png
```

## 接入方式

```bash
git clone https://github.com/feeling6667/baicat.git
```
放到 skills 目录（如 `/var/minis/skills/baicat/`），Agent 自动识别 `SKILL.md`。

## 设计原则

- **AI 不当裁判**：不打分不评级。机械判定给脚本，品味判断给博主，客观分给发布数据。
- **先讲透再画**：故事核、钩子、结局、视觉基调、人物卡都在出图前定好，不返工。
- **逻辑优先于效果**：反转/留白/情绪不能让位于逻辑漏洞。
- **配方驱动**：画风 prompt 存 `STYLES.md`，脚本不缩写，画风不漂移。
- **留白为主**：生图不画字，顶部约1/3大留白区后期加字，画面上缘淡入留白无硬分界，给情绪留呼吸空间。
- **越用越懂你**：每篇登记指纹，数据回流后组合分析反哺下批选题。

## License

[MIT](LICENSE) © feeling6667

minis_url: minis://skills/baicat/README.md
