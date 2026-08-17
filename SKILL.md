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

**约束**：手写体文字是画面一部分（与涂鸦风格相反）；排线阴影而非色块；低饱和不鲜艳。

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
  --style doodle|colored-pencil
```

故事 JSON 格式：
```json
{
  "title": "等",
  "style": "doodle",
  "anchor": "optional/path/anchor.png",
  "panels": [
    {
      "id": "p1",
      "scene": "A girl sitting on a chair hugging knees, quietly waiting. Red hair clip.",
      "text": "旁白：等一个人。\n对话气泡：你在哪？"
    },
    {
      "id": "p2",
      "scene": "Same pose, calendar page flipped, sky dimmer.",
      "text": "旁白：她还在等。"
    }
  ]
}
```
`anchor` 可选；不填则第 2 格起自动用上一格输出当画风参考。
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

- **文字必须画进图里** — 对话和旁白写进生图 prompt 的 `【文字】`，让 GPT Image 2 直接画在图里，不要放在图外
- **人物造型各格一致** — 同一故事内风格统一；连续分镜用 anchor 锚点图或逐格参考锁定
- **配方驱动** — 画风 prompt 存 `STYLES.md`，脚本只负责提取+填占位符，禁止手工缩写配方
- **配方不锁角色** — 人物外貌由故事内容决定，配方不写死角色描述，各格保持一致即可
- **留白为主** — 不要把画面填满
- **涂鸦风格文字写在画面上方留白区或对话气泡内**；**彩铅风格文字是画面一部分**
- **涂鸦只有一种红色**；**彩铅低饱和多色但克制**
- **中文必须清晰可读** — 配方已写死 "no garbled or fake characters" 约束
