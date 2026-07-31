---
name: baicat
description: >
  Generate hand-drawn doodle comic (手绘涂鸦条漫) style illustrations and multi-panel story pages.
  Use when the user asks to "画一个故事", "生成条漫", "做个漫画故事", "doodle comic",
  "手绘涂鸦风格", or wants to create emotional slice-of-life story panels in
  black-and-white ink sketch style with a single red accent color.
  Covers style prompt engineering, story scripting, batch image generation,
  and HTML story page assembly.
---

# baicat — 手绘涂鸦条漫故事生成器

## 风格定义

**核心风格**：手绘涂鸦条漫 / 黑白线稿 + 单一红色点缀 / Q版简笔 / 丧系情绪

| 维度 | 特征 |
|------|------|
| 画风 | 手绘涂鸦式条漫，日记感+随笔感，草稿速写 |
| 色彩 | 黑白线稿为主，**唯一彩色是高饱和红色点缀**（发夹/手机屏幕/小物件） |
| 线条 | 粗犷、不规整、有抖动，线宽变化，边缘不闭合，阴影用排线 |
| 构图 | 条漫分镜式，主体居中，大量白底留白 |
| 人物 | Q版简笔：头大身小，豆豆眼/黑点眼，凌乱卷发，面无表情→疲惫 |
| 情绪 | 冷静、自嘲、略带讽刺，清醒中带孤独，轻微emo |

## 风格 Prompt 模板

所有生图调用复用此模板，仅替换 SCENE 部分：

```
Hand-drawn doodle comic style illustration.
Black and white rough ink line art on clean white background.
The ONLY color in the image is ONE bright red element.
Sketchy, trembling, casual ink lines with unfinished edges and spontaneous linework.
Minimalist Q-version character: big head small body, simple dot eyes, messy tousled hair.
Lots of white negative space, centered subject.
Diary-style emotional illustration, melancholic yet humorous mood.
No text, no speech bubbles, no words, no letters anywhere in the image.

SCENE: {在这里填入每格的画面描述}
```

## 工作流

### 1. 写故事脚本

将用户主题拆成 6-10 格条漫分镜，每格包含：
- **画面**：用一句话描述场景动作（不写文字/对话）
- **文案**：放在图片下方/上方的短句（≤15字）

情绪线设计：从一个状态渐变到另一个状态（如：期待→麻木→释然）。

### 2. 批量生成图片

用 `scripts/generate_story.py` 批量生成：

```bash
python3 /var/minis/skills/baicat/scripts/generate_story.py \
  --story-json <故事JSON文件> \
  --output-dir <输出目录>
```

故事 JSON 格式：
```json
{
  "title": "等",
  "panels": [
    {"id": "p1", "scene": "A girl sitting on a chair hugging knees, quietly waiting. Red hair clip. Phone on table."},
    {"id": "p2", "scene": "Same pose, calendar page flipped, sky dimmer."}
  ]
}
```

脚本会逐格调用 GPT Image 2（通过代理），保存为 `{output_dir}/story_p1.jpeg` 等。

**生图 API 细节**：
- 端点：`$IMAGE_API_URL/images/generations`（环境变量 `IMAGE_API_URL`）
- 模型：`gpt-image-2`
- 尺寸：`1024x1536`（竖屏条漫比例）
- 质量：`high`
- 返回：`b64_json`，需 base64 解码保存为 JPEG

### 3. 组装图文故事页面

用 `templates/story_page.html` 模板生成最终 HTML 页面：
- 替换 `{{TITLE}}` 为故事标题
- 复制 panel 块，替换图片文件名和文案
- 红色文案用 `<span class="red">` 包裹

## 关键约束

- **禁止在图中出现任何文字** — 文案单独放在图片下方
- **每格只有一个红色元素** — 不要多色
- **人物造型保持一致** — 同一个故事的各格人物风格统一
- **留白为主** — 不要把画面填满
