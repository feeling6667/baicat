---
name: baicat
description: "生成手绘涂鸦风格（doodle）漫画故事插画和多格条漫页面，含两种风格：①「涂鸦」黑白墨线+单一红色点缀、Q版角色、黑色幽默；②「彩铅」低饱和色调、铅笔/石墨质感、写实比例、治愈氛围。当用户要求\"画一个故事\"、\"生成条漫\"、\"做个漫画故事\"、\"涂鸦风格\"、\"彩铅风格\"、\"doodle comic\"、\"colored pencil\"，或想创作治愈系生活切片故事分镜时使用。涵盖风格提示词工程、故事脚本、批量出图、HTML 故事页组装。"
  Generate hand-drawn comic story illustrations and multi-panel pages in TWO styles.
  Style 1 「涂鸦」(doodle): black-and-white ink sketch + single red accent, Q-version characters, melancholic humor.
  Style 2 「彩铅」(colored-pencil): muted desaturated palette, pencil/graphite texture, realistic proportions, healing atmosphere.
  Use when the user asks to "画一个故事", "生成条漫", "做个漫画故事", "涂鸦风格", "彩铅风格",
  "doodle comic", "colored pencil", or wants to create emotional slice-of-life story panels.
  Covers style prompt engineering, story scripting, batch image generation, and HTML story page assembly.
---

# baicat — 双风格条漫故事生成器

## 两种风格

用户调用时输入风格名即可选择，不指定则默认「涂鸦」。

| 中文名 | 英文名 | 触发词 | 一句话描述 |
|--------|--------|--------|-----------|
| **涂鸦** | doodle | 涂鸦、黑白涂鸦、丧系涂鸦 | 黑白线稿 + 红色点缀，Q版简笔，丧系自嘲 |
| **彩铅** | colored-pencil | 彩铅、彩色铅笔、治愈条漫 | 低饱和高级灰，铅笔排线，真实比例，治愈克制 |

---

## 风格 A：涂鸦

| 维度 | 特征 |
|------|------|
| 画风 | 手绘涂鸦式条漫，日记感+随笔感，草稿速写 |
| 色彩 | 黑白线稿为主，**唯一彩色是高饱和红色点缀**（发夹/手机屏幕/小物件） |
| 线条 | 粗犷、不规整、有抖动，线宽变化，边缘不闭合，阴影用排线 |
| 构图 | 条漫分镜式，主体居中，大量白底留白 |
| 人物 | Q版简笔：头大身小，豆豆眼/黑点眼，凌乱卷发，面无表情→疲惫 |
| 情绪 | 冷静、自嘲、略带讽刺，清醒中带孤独，轻微emo |
| 文字 | **手写体黑色中文写在画面上方留白区**，也可用手绘对话气泡 |

**Prompt 模板：**
```
Hand-drawn doodle comic style illustration.
Black and white rough ink line art on clean white background.
The ONLY color in the image is ONE bright red element.
Sketchy, trembling, casual ink lines with unfinished edges and spontaneous linework.
Minimalist Q-version character: big head small body, simple dot eyes, messy tousled hair.
Lots of white negative space, centered subject in the LOWER portion of the image.
The TOP THIRD of the image is deliberately left blank white space for hand-lettered Chinese text.
Black hand-drawn Chinese characters in the top blank area, slightly wobbly and uneven like a casual diary note.
Diary-style emotional illustration, melancholic yet humorous mood.
Speech bubbles are allowed: rough hand-drawn oval outlines with black text inside.

SCENE: {画面描述}
```

**约束**：每格只有一个红色元素；人物造型各格一致；文字写在画面上方留白区或对话气泡内。

---

## 风格 B：彩铅

| 维度 | 特征 |
|------|------|
| 画风 | 彩铅/铅笔质感数字插画，纸张颗粒感，手账扫描感 |
| 色彩 | 低饱和高级灰：蓝灰、米白、黑棕、浅肤色、暖黄点缀；靠冷暖对比推进情绪 |
| 线条 | 细 loose 手绘线，深灰/黑棕色，无粗黑描边；阴影用平行排线/交叉排线 |
| 构图 | 竖版条漫，上方大面积留白给文字，人物偏小偏下，多背影/侧影/低头 |
| 人物 | 接近真实比例（5-6头身），短发微乱，身形纤细，圆点眼/小鼻/细线嘴，脸颊淡红 |
| 情绪 | 孤独、压抑、克制中透出温暖希望，安静有力量 |
| 文字 | **手写体黑色中文直接写在画面上方**，像日记旁白 |

**Prompt 模板：**
```
A healing hand-drawn webcomic illustration with colored pencil and graphite texture,
muted desaturated palette. Short-haired woman, back view or front view, wearing oversized
blue shirt and dark pants, slender figure, calm expression with hint of sadness.
Minimalist indoor background: white wall, corner or window. Large negative space at top
for hand-lettered black Chinese text like diary narration. Loose hand-drawn lines, pencil
hatching for shadows, no thick black outlines. Paper grain texture visible.
Color scheme: grey-blue, off-white, dark brown, warm yellow.
Quiet, lonely, restrained atmosphere with subtle hope.

SCENE: {画面描述}
```

**Prompt 模板：**
```
A healing hand-drawn webcomic illustration with colored pencil and graphite texture,
treated as a 写实彩铅手绘叙事插画 (realistic colored-pencil narrative illustration),
muted desaturated 莫兰迪 palette. 细腻彩铅叠色笔触, 自然手绘肌理, 柔和阴影.
复古米色画纸质感, 电影感叙事构图, 画面干净克制, 色彩淡雅不艳丽, 细节丰富, 8K高清.

【光影】. 【画纸】.

Loose hand-drawn lines, pencil hatching for shadows, no thick black outlines.
Paper grain texture visible.
Quiet, lonely, restrained atmosphere with subtle hope.
Minimalist indoor background. Large negative space at top for bold thick black hand-lettered Chinese text.

SCENE: {画面描述}

Draw the following exact Chinese text directly into the image at the top blank area.
Use bold, thick, black hand-lettered strokes. No labels, no prefixes like "旁白" or "对话" or "字幕".
All Chinese text must be clearly readable, no garbled or fake characters.

TEXT:
{中文文字}
```

**约束**：手写体文字是画面一部分（与涂鸦风格相反）；排线阴影而非色块；低饱和不鲜艳。

---

## 抗同质化变量机制（V2，重点）

为规避抖音等平台把同一套画风判定为"AI 批量生图"，彩铅配方内置**光影 + 画纸变量**：

- `【光影】`：6 套光影氛围（日常柔和 / 窗边逆光 / 冷调柔光 / 硬光 / 黄昏暖调 / 室内顶光），
  存在 `STYLES.md` 的「光影氛围变量库」。
- `【画纸】`：5 套画纸纹理（细颗粒米色 / 粗纹 / 泛黄斑驳 / 折痕磨损 / 哑光浅灰），
  存在 `STYLES.md` 的「画纸纹理变量库」。

**使用规则**：
1. **同一篇内**：全程用同一套「光影+画纸」，保证单篇氛围统一（脚本自动锁死）。
2. **光影自动推断（推荐，零负担）**：不填 `lighting` 时，脚本会扫描整篇故事
   （title + 每格 scene/text）的**情绪关键词**，自动匹配最贴合的光影序号——
   温馨→#1 回忆遗憾→#2 emo/释怀→#3 扎心反转→#4 怀旧→#5 清醒释然→#6。
   （手动指定 `lighting` 永远优先于推断。）
3. **画纸自动轮换**：画纸是质感变量、与情绪弱相关，每篇自动挑最久未用的纹理。
4. **抗同质化**：脚本把组合记录进 skill 根目录 `USAGE.json`，跨篇尽量不重复；
   手动指定光影时会从未用池剔除，避免冲突。
5. **手动指定**：story JSON 加 `"lighting": 3`（1-6）和 `"paper": 2`（1-5）；
   或命令行 `--lighting 3 --paper 5`。
6. **查库**：`python3 generate_story.py --list-variants` 可查看全部光影/画纸库。
   运行时会打印 `[变量] 光影#N（情绪自动推断/自动轮换/手动指定）` 供核对。

> **⚠️ 强制流程约定（对话提醒）**：每当脚本跑完一批图（出现 `Done! All panels saved
> to: ...`），**助手必须在同一轮对话里主动向用户发出醒目的二次加工提醒**，内容含：
> ① 这批图已生成完 + 光影/画纸组合；② 提醒走醒图三步骤（详见
> `references/抗同质化手工流程.md`）；③ 提醒出图参数与发布数据要填进
> `references/数据复盘表.md`。不许静默结束而不提醒。

**二次加工**（消除流水线 AI 特征，每篇必做）：
AI 出图后用醒图做轻量人工痕迹加工，详细 SOP 见
`references/抗同质化手工流程.md`，每篇参数记录进 `references/数据复盘表.md`。
核心就三点：参数微调（色温/阴影/颗粒/对比，数值打散）+ 空白处补少量彩铅排线 +
边角放专属小标记（每篇换位置）。

**数据复盘**：每篇发布后回填 `references/数据复盘表.md`，用首图划走率/完播率/评论量
反向优化脚本与选题（判定标准见该文档末尾）。

---

## 彩铅双分镜构图标准（V3，重点）

**适用**：仅彩铅风格；**当故事总格数 >6 时自动启用双分镜**（≤6 格仍逐格单图）。
脚本通过 `--split2` 或 story JSON `"split2": true` 开启，脚本会自动判定是否 >6 格。

**核心规则**：
1. **一个 3:4 画布放两个分镜**：单张竖版 3:4（1024×1536）画布内划分上下两个叙事画面。
2. **分镜分隔 = 极淡浅灰细线**：用约 `#d9d9d9` 的极淡浅灰色细线隔开，**禁止粗黑漫画边框**。
   脚本用 Pillow 拼接，分隔线已内置该色。
3. **每个分镜上方预留干净留白区**：旁白文字由生图时直接画进该留白区，构图不拥挤。
4. **光影色调统一**：同一张图内上下两分镜光影色调必须统一；整套多张图保持统一
   画纸纹理 + 光影风格（光影/画纸本就同一篇锁一套，自动满足）。
5. **细节完整不压缩**：分镜构图均衡、元素不拥挤，彩铅手绘细节完整清晰、不压缩笔触质感。
   脚本对每个分镜单独以 1024×1024 高清生成后再拼接，而非一次塞进同图，保证笔触不糊。

**产物结构（以 8 格为例）**：
- 第 1 格 → `story_<id>.jpeg`：**封面，必为单图**
- 第 2+3、4+5、6+7 格 → `story_split_<a>_<b>.jpeg`：双分镜图（1024×1536）
- 末尾若多余 1 格 → 该格单独成图

**图内旁白标准**：
- 首选：单行短句（≤20 字），每格顶部居中、黑色粗体手写。
- 特殊扩容：最多两行、总字数 ≤35 字，**仅复杂剧情节点启用，不可通篇使用**。

**信息分工**：
- 画面 + 图上旁白：承载故事**主线骨架**与视觉情绪。
- 作品正文（HTML/推文正文）：补充**人物背景、对话、细节铺垫、完整故事逻辑**。
- 即：图上只给主线留白短句，背景与前因后果放正文文字，二者互补不重复。

**封面约束**：**封面必须是单图，不能一图两格**。封面用完整竖版 3:4 单格构图，
不同时容纳两个分镜，保证首图信息聚焦、划走率低。

**发布辅助**：正文结尾放置一个**开放式互动提问**，引导观众评论区作答、提升评论率。

---

## 工作流

### 1. 确认风格

用户说"涂鸦"→ 风格 A；用户说"彩铅"→ 风格 B；未指定 → 询问或默认涂鸦。

### 2. 写故事脚本

将用户主题拆成 6-10 格条漫分镜，每格包含：
- **scene（画面）**：一句话描述场景动作（英文，填入配方的 `【主体】`）
- **text（文字）**：要画进图里的中文（对话气泡台词 + 旁白字幕），填入配方的 `【文字】`。**必须写进生图 prompt，让 GPT Image 2 把中文直接画在图里，而不是放在图外。**

情绪线设计：从一个状态渐变到另一个状态（如：期待→麻木→释然）。

### 3. 批量生成图片

用 `scripts/generate_story.py` 批量生成：

```bash
python3 /var/minis/skills/baicat/scripts/generate_story.py \
  --story-json <故事JSON文件> \
  --output-dir <输出目录> \
  --style doodle|colored-pencil \
  --split2        # 可选：彩铅>6格启用双分镜（或用 JSON 里 "split2": true）
```

故事 JSON 格式：
```json
{
  "title": "等",
  "style": "colored-pencil",
  "anchor": "optional/path/anchor.png",
  "lighting": 3,          // 可选：光影变量 1-6；不填则按情绪自动推断（推断不出走轮换）
  "paper": 2,             // 可选：画纸变量 1-5；不填则自动轮换
  "split2": true,         // 可选：双分镜模式；总格数>6 才真正生效，第1格作封面单图
  "panels": [
    {
      "id": "p1",
      "scene": "A girl sitting on a chair hugging knees, quietly waiting. Red hair clip.",
      "text": "等一个人。"    // 图上旁白：单行≤20字；复杂节点最多两行≤35字
    }
  ]
}
```
`anchor` 可选；不填则第 2 格起自动用上一格输出当画风参考。
`lighting` / `paper` 可选；仅彩铅配方生效，不填由脚本自动轮换抗同质化。
`text` 必填——文字直接画进图里，不要放在图外。

脚本从 `STYLES.md` 读取对应画风的配方代码块，自动填充 `【主体】` 和 `【文字】` 占位符（配方驱动，不写死在脚本里，加画风只改 STYLES.md 不改脚本），逐格调用 GPT Image 2，保存为 `{output_dir}/story_p1.jpeg` 等。

**画风一致性机制（连续分镜锁风格）**：
故事 JSON 可选 `anchor` 字段指定一张画风锚点图；设定后每格生成都把它作为 style-only 参考传入，锁定多格画风一致（只继承线条/配色/比例/氛围，不复制人物服装站位）。未指定 anchor 时，第 2 格起自动用上一格输出作为参考，保证连贯。

**生图 API 细节**：
- 端点：`$IMAGE_API_URL/images/generations`（环境变量 `IMAGE_API_URL`）
- 模型：`gpt-image-2`
- 尺寸：`1024x1536`（竖屏条漫比例）
- 质量：`high`
- 返回：`b64_json`，需 base64 解码保存为 JPEG

**IMAGE_API_URL 未设时的替代路线**：
iSH 环境可能没有 `IMAGE_API_URL`。此时脚本的 urllib 直调路线跑不了，改用 `minis-model-use`：
```bash
minis-model-use run --model gpt-image-2 --endpoint images-gen --input req.json --output out.png
```
req.json 的 messages 里放完整 prompt（配方提取 + 填充后的文本），generation_config 放 size 和 n。

### 4. 组装图文故事页面

用 `templates/story_page.html` 模板生成最终 HTML 页面：
- 替换 `{{TITLE}}` 为故事标题
- 复制 panel 块，替换图片文件名
- **纯图片竖排模式**：文字全部画在图里，HTML 不再放图外文案
- 图片放在与此 HTML 同一目录下

## 关键约束

- **文字必须画进图里** — 对话和旁白写进生图 prompt 的 `【文字】`，让 GPT Image 2 直接画在图里，不要放在图外；双分镜模式下旁白按"每格顶部居中黑色粗体、单行≤20字"标准控制
- **人物造型各格一致** — 同一故事内风格统一；连续分镜用 anchor 锚点图或逐格参考锁定
- **彩铅>6格用双分镜** — 总格数>6 时启用 `split2`：1格封面单图 + 其余相邻两格拼一张 3:4 双分镜图（极淡浅灰细线分隔，禁止粗黑边框）；封面必为单图
- **信息分工** — 画面+图上旁白承载主线骨架与视觉情绪；人物背景/对话/细节/完整逻辑放作品正文；正文结尾放开放式互动提问
- **配方驱动** — 画风 prompt 存 `STYLES.md`，脚本只负责提取+填占位符，禁止手工缩写配方
- **配方不锁角色** — 人物外貌由故事内容决定，配方不写死角色描述，各格保持一致即可
- **留白为主** — 不要把画面填满
- **涂鸦风格文字写在画面上方留白区或对话气泡内**；**彩铅风格文字是画面一部分**
- **涂鸦只有一种红色**；**彩铅低饱和多色但克制**
- **中文必须清晰可读** — 配方已写死 "no garbled or fake characters" 约束
