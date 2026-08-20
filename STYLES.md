# baicat 故事画风配方库

每段是一个画风的生图 prompt 模板。`generate_story.py` 按风格名读取对应代码块，
原样提取、自动填充占位符，禁止手工缩写或同义改写。
配方改动只改本文件，不改脚本。

占位符说明：
- `【主体】`：单格画面场景描述（由故事脚本的 panel.scene 填入），必填。
- `【文字】`（仅 doodle 涂鸦配方使用）：要画进图里的中文文字（对话气泡台词 + 旁白字幕），由 panel.text 填入。
  生图时必须把这段中文写进 prompt，让 GPT Image 2 把文字画在图里，而不是放在图外。
  **colored-pencil 彩铅配方不含此占位符** —— 彩铅生图**不画任何文字**，只留出顶部空白旁白区，文字由作者后期手动添加。
- `【光影】且含变量库`（仅 colored-pencil）：光影氛围变量，来自下方"光影氛围变量库"，
  由 story JSON 的 `lighting` 字段指定或用库内轮换。**同一篇内所有格共用同一套，跨篇轮换。**
- `【画纸】且含变量库`（仅 colored-pencil）：画纸纹理变量，来自下方"画纸纹理变量库"，
  规则同光影。**光影+画纸的组合同一篇内锁定、跨篇尽量不重复。**

---

## 光影氛围变量库（仅 colored-pencil 用）

```
1. 柔和正面漫射平光，均匀弱阴影，日常温馨叙事氛围
2. 窗边侧逆光，明暗对比适中，柔和阴影，回忆与遗憾氛围
3. 弱冷调柔光，低对比灰彩色调，释怀与克制氛围
4. 局部硬光影，明暗对比强烈，紧张与扎心氛围
5. 黄昏暖调漫射光，大面积柔和暗角，怀旧与回望氛围
6. 室内顶光，浅淡柔和阴影，通透干净，清醒与释然氛围
```

## 画纸纹理变量库（仅 colored-pencil 用）

```
1. 平整细颗粒米色彩铅画纸，轻微纸张纤维肌理
2. 粗纹彩铅专用画纸，明显纸张纹路
3. 复古泛黄旧画纸，少量自然浅褐色斑驳痕迹
4. 带轻微折痕的彩铅画纸，边缘淡淡磨损质感
5. 哑光浅灰画纸，基底干净几乎无杂色
```

---

## doodle 涂鸦

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

SCENE: 【主体】

TEXT IN IMAGE (draw these exact Chinese characters into the image, in speech bubbles or narration areas):
【文字】
All Chinese text must be clearly readable, hand-lettered in black, no garbled or fake characters.
```

约束：每格只有一个红色元素；人物造型各格一致；文字写在画面上方留白区或对话气泡内；中文必须清晰可读无乱码。

---

## colored-pencil 彩铅

```
A healing hand-drawn webcomic illustration with colored pencil and graphite texture,
treated as a 写实彩铅手绘叙事插画 (realistic colored-pencil narrative illustration),
muted desaturated 莫兰迪 palette. 细腻彩铅叠色笔触, 自然手绘肌理, 柔和阴影.
复古米色画纸质感, 电影感叙事构图, 画面干净克制, 色彩淡雅不艳丽, 细节丰富, 8K高清.

【光影】. 【画纸】.

【构图】

Loose hand-drawn lines, pencil hatching for shadows, no thick black outlines, no comic frames.
Paper grain texture visible. Balanced uncluttered composition, subject not crowded against edges,
full sharp colored-pencil detail, pencil stroke texture kept intact and uncompressed.

【分镜结构】

Quiet, lonely, restrained atmosphere with subtle hope.

A full-width clean blank band is reserved at the very top of the image (and at the top of
each panel in split composition) as a narration area. Keep this blank band COMPLETELY EMPTY:
do NOT draw any Chinese text, character, letter, label or watermark in the image.
No handwritten narration, no subtitles, nothing — the narration will be added later by hand,
so this reserved band must stay clean paper-colored and free of any marks.

SCENE: 【主体】
```

约束：
- 光影+画纸变量同一篇内锁定一套、跨篇轮换不重复；双分镜模式下同一张图的上下两分镜、以及整套所有分镜与封面，都必须共用同一套光影+画纸，保证整篇氛围统一。
- **双分镜标准（仅 colored-pencil，故事总格数>6 时自动启用）**：
  - 单张竖版 3:4（1024x1536）画布内划分上下两个叙事画面。
  - 分镜分隔用一条**极淡浅灰色细线**（约 #d9d9d9），**禁止粗黑漫画边框**。
  - 每个分镜上方预留干净留白区；**生图时不画任何文字**，旁白由作者后期手动添加入该留白区。
  - 同一张图内上下两分镜光影色调统一；分镜构图均衡、元素不拥挤，彩铅手绘细节完整清晰、不压缩笔触质感。
- **封面必为单图**，不能一图两格（封面用竖版单格完整构图，不同时容纳两格）。
- **彩铅生图不画文字**：竖版单图和双分镜都在顶部留干净留白区，画面内不写任何中文/字符/水印；
  旁白文字由作者后期添加。
- **后期旁白排版规范**：单行短句（≤20字）、每格顶部居中黑色粗体；特殊扩容最多两行、总字数≤35字，仅复杂剧情节点启用，不可通篇使用。
- 排线阴影而非色块；低饱和不鲜艳；配方不锁定角色外貌——人物由故事内容决定，各格保持一致即可。

minis_url: minis://skills/baicat/STYLES.md
