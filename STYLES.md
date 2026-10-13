# baicat 故事画风配方库

每段是一个画风的生图 prompt 模板。`generate_story.py` 按风格名读取对应代码块，
原样提取、自动填充占位符，禁止手工缩写或同义改写。
配方改动只改本文件，不改脚本。

占位符说明：
- `【主体】`：单格画面场景描述（由故事脚本的 panel.scene 填入），必填。
- **两风格生图默认自带旁白字**：doodle 涂鸦与 colored-pencil 彩铅默认都把 `text` 以一行
  乐米蜡笔体（儿童蜡笔手写体，V3.4 起全风格统一）画进顶部留白（脚本追加 NARRATION TEXT 覆盖块实现，配方本体不变，仍是留白结构）。
  关闭后（`--no-text-in-image`/JSON false）出纯无字底图，旁白由作者用 letter_baicat 后期加。
  `text` 字段始终兼作剧情与光影情绪推断的记录。
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
The TOP THIRD of the image is deliberately left blank white space as a narration area.
Keep this top blank band COMPLETELY EMPTY: do NOT draw any Chinese text, character, letter,
label or watermark in the image. No narration, no subtitles, no handwriting — the narration
will be added later by hand, so this reserved band must stay clean white and free of any marks.
Diary-style emotional illustration, melancholic yet humorous mood.

SCENE: 【主体】
```

约束：每格只有一个红色元素；人物造型各格一致；**生图默认自带旁白字**（乐米蜡笔体画进顶部留白；`--no-text-in-image` 关闭后留白区完全留空，旁白后期用 letter_baicat 加）；若需对话气泡轮廓可后期绘制再填字。

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

A LARGE clean blank paper area covering roughly the TOP THIRD of the image (and the top
third of each panel in split composition) is reserved as a narration area. Keep this blank
area COMPLETELY EMPTY: do NOT draw any Chinese text, character, letter, label or watermark
in it — no narration, no subtitles, nothing; the narration will be added later by hand.
The blank area is pure paper color: no pencil strokes, no objects, no horizon, no texture
marks inside it. The scene below breathes into it: the upper background of the drawing
fades softly and gradually into the blank paper — no hard edge, no visible boundary line —
leaving an airy, minimalist page where emptiness dominates the top.

SCENE: 【主体】
```

约束：
- 光影+画纸变量同一篇内锁定一套、跨篇轮换不重复；双分镜模式下同一张图的上下两分镜、以及整套所有分镜与封面，都必须共用同一套光影+画纸，保证整篇氛围统一。
- **双分镜标准（仅 colored-pencil，故事总格数>6 时自动启用）**：
  - 单张竖版 3:4（1024x1536）画布内划分上下两个叙事画面。
  - 分镜分隔用一条**极淡浅灰色细线**（约 #d9d9d9），**禁止粗黑漫画边框**。
  - 每个分镜上方预留**约1/3大留白区**（分镜单元按 35% 留白生成，拼接居中裁切后成图每格仍保住约30%）；**旁白默认由生图直接画进该留白区**（乐米蜡笔体式儿童蜡笔手写体，text_in_image 默认开；关闭后才走后期 letter_baicat 加字，字体同样是乐米蜡笔体）。
  - 同一张图内上下两分镜光影色调统一；分镜构图均衡、元素不拥挤，彩铅手绘细节完整清晰、不压缩笔触质感。
- **封面必为单图**，不能一图两格（封面用竖版单格完整构图，不同时容纳两格）。
- **彩铅生图不画文字**：竖版单图和双分镜都在顶部留**约1/3大留白区**（纯纸色、上缘无分界线），画面内不写任何中文/字符/水印；
  旁白文字由作者后期添加。
- **大留白版式**：竖版单图顶部约 1/3 为纯纸色留白，画面集中下方 2/3；画面上缘背景自然淡入留白、无硬边界，"上空下画"、疏朗呼吸感。
- **后期旁白排版规范**：单行短句（≤20字）、每格顶部居中黑色粗体；特殊扩容最多两行、总字数≤35字，仅复杂剧情节点启用，不可通篇使用。
- 排线阴影而非色块；低饱和不鲜艳；配方不锁定角色外貌——人物由故事内容决定，各格保持一致即可。

---

## colored-pencil-airy 彩铅留白（高调清爽版，V3.3 新增）

> 2026-09-13 实测新增。解决旧彩铅"米色纸纹+全局颗粒"满铺导致的画面显脏问题。
> 参考对象：抖音「一只漫仔」——纯白底摆人、背景 1-2 件必需品、黑字+红关键词。

```
A colored pencil illustration in a bright, airy, high-key style. Vertical composition.

LAYOUT (strict): The top one third of the canvas is PURE FLAT WHITE paper containing ONLY
the caption text. The text zone is clean white with NO paper grain, NO texture, NO gradient,
and there is a clean hard boundary between the text zone and the illustration below —
no fading, no transition, no gradient wash between text zone and drawing.

ILLUSTRATION (bottom two thirds): 【主体】
Colored pencil hatching texture appears ONLY on the characters and their key props —
soft muted pastel colors (pale blue, warm gray, cream skin tone). Everything else stays
pure white.

BACKGROUND: eighty percent empty pure white space. At most ONE or TWO background objects,
sketched in very light pale-gray pencil lines, barely visible, left uncolored. Absolutely
NO walls, NO windows, NO full room, NO floor, NO shadows, NO large dark areas, and NO
global paper texture — characters float on white paper.

TEXT ON IMAGE (must be written exactly, simplified Chinese; the caller replaces {{caption}}
with the actual narration lines, one line each; mark exactly ONE key phrase in bright red,
all other characters pure black; the red phrase appears ONLY in the caption):
{{caption}}

No other text anywhere in the image. Any screen or sign contains only illegible blurred
text blocks. No brand logos, no watermarks, no signatures.
```

约束：
- **与旧彩铅（colored-pencil）的核心区别**：旧版"复古米色纸+全局纸纹+文字区上缘淡入"，airy 是"纯白底+颗粒只上人物+文字区硬分界"。airy **不使用【光影】【画纸】变量库**（那两套变量会把米色纸纹带回全图，前功尽弃）。
- **颗粒纪律**：彩铅质感/排线只许出现在人物与关键道具上；背景、留白区、文字区一律无颗粒无纸纹。
- **背景做减法**：1-2 件必需品、淡灰线稿不上色；禁墙/窗/地面/阴影；人物"浮"在白纸上。
- **高调明度**：禁大面积暗部；重色只允许出现在头发线条、旁白黑字与红词上。
- **红字纪律**：每格旁白只标 1 处关键词（情绪重音），全图除该词外无红色元素。
- **硬分界**：上 1/3 纯白文字区与下 2/3 画面之间干净分界，**不做渐变淡入**（与旧彩铅的"上缘自然淡入"相反，二选一不可混用）。
- **旁白机制**：`{{caption}}` 由调用方填入实际旁白（可多行，每行一句）。脚本 `generate_story.py` 默认追加的单行黑字覆盖块与 airy 的"多行+红词"不兼容——airy 带 2 行以上旁白或需要红词时，由 AI 手工拼装 prompt 直调生图（如 minis-model-use），不走脚本默认旁白块；单行且不需红词时可正常走脚本。
- 可与 split2 双分镜共用：分隔线沿用极淡浅灰细线（约 #d9d9d9），每个分镜单元同样"上 1/3 纯白字区 + 下 2/3 留白画面"，字区与画面单元间同样硬分界。
- 实测记录（2026-09-13，GPT Image 2，1024x1536）：《轻得像张废纸》p05 重制一次通过——21 字旁白逐字零错、红词精准标红、背景仅课桌角一个淡线稿元素、无脏颗粒；新旧对比图 `/var/minis/workspace/baicat_轻得像张废纸/对比_旧vs新_p05.jpg`。

---

## frazee 绘本水彩（FB-060 · Marla Frazee）

> 来源：handraw-style 风格库 **FB-060 · Marla Frazee Playful Childlike Pencil & Watercolor Storybook**
> （原库编号 #316，分组 FB 经典绘本叙事；参考绘本作者 Marla Frazee）。2026-10-13 引入 baicat。
>
> **画风段严格按原库规范写**：原库 SKILL.md 明令「不得自创画风特征、不得追加通用构图/质量套话」，
> 提示词只由三段组成 —— `Style name: {generation_name}.` + `Reference author/style name: {作者}.`
> + `Core style traits: {原库 traits 原样}`。本配方照此逐字填入，**没有添加任何自编画风描述**。
>
> **要不要垫参考图**：原库判定脚本实测 `resolve_reference.py --model gpt-image-2 --style FB-060`
> → `activation_source = name+style+traits`、`use_reference_image = false`，即**不需要垫图**。
> skill 内仍保留原库样图 `references/style-refs/FB-060-marla-frazee.webp` 供人工比对；
> 想强制垫图时，story JSON 写 `"style_reference": "<该图路径>"`（脚本会追加只参考画风的隔离指令）。

```
Style name: Marla Frazee Playful Childlike Pencil & Watercolor Storybook.
Reference author/style name: Marla Frazee.
Core style traits: 参考绘本作者Marla Frazee.

【光影】. 【画纸】.

【构图】

【分镜结构】

SCENE: 【主体】
```

约束：
- **画风段只许上面那三行**，禁止再往里塞线条/配色/人物长相之类的自编描述（原库硬规则）。
  要最纯净的原库版：只留那三行 + 你的主题，把下面 baicat 自己的层也去掉。
- **【光影】【画纸】是 baicat 自己的防同质化层**（跨篇轮换，避免同画风被判 AI 批量图），不是原库内容；
  同一篇锁一套、脚本自动锁死并记进 `USAGE.json`。
- **【构图】【分镜结构】是 baicat 的版式要求**（顶部约1/3纯纸色留白给旁白；split2 上下拼接），
  属格式约束，不改画风。
- **旁白字体统一乐米蜡笔体**：默认 `text_in_image` 把旁白画进图（prompt 已写明该笔感）；
  关掉后走 `letter_baicat.py --auto` 用真实字体文件确定性加字。
- **支持 split2 双分镜**（总格数 >6）；**不支持整页多格 multipanel**。
- **适用题材**：温情、童趣、成长、亲子、治愈、童年回忆；暗黑压抑题材仍走 `colored-pencil`。

---

## colored-pencil-page 彩铅整页多格（原生生图）

```
A healing hand-drawn webcomic page, realistic colored-pencil narrative illustration on paper.
muted desaturated 莫兰迪 palette, 细腻彩铅叠色笔触, 自然手绘肌理, 复古米色画纸质感.
【光影】. 【画纸】.

Compose the ENTIRE comic page in ONE image with a clear editorial rhythm:
- TOP: one LARGE horizontal anchor panel (the strongest/most emotional beat).
- MIDDLE: a row of 2 to 3 SMALLER panels side by side (detail / reaction beats).
- BOTTOM: one LARGE horizontal closing panel (the reveal or final beat).
Panels are UNEQUAL in size and clearly separated from each other by clean WHITE
borders and visible white gutter spacing between them — like a printed comic page,
NOT an equal grid, NOT touching edges. Each panel is a self-contained scene showing
its full composition; no cropping, no overlap, nothing cramped.
The same recurring character (same hair, build, clothing) appears consistently across
all panels.

Inside each panel, leave a generous blank paper band at the top (about the top quarter to
a third of the panel) for narration (narration is added later), so keep the upper area of
every panel calm, empty and uncluttered.
Draw NO Chinese characters, NO text, NO labels, NO watermark anywhere in the image.

Loose hand-drawn lines, pencil hatching shadows, no thick outlines, paper grain visible.
Quiet, restrained, cinematic mood.

PAGE LAYOUT AND PANELS (describe every panel, reading order top→bottom):
【主体】
```
约束：整页一次生成，不逐格拼接；格子非等分有节奏但绝不被裁切；同一主角跨格一致；每格顶部约1/4~1/3留白不画字；
光影+画纸整篇统一一套；中文旁白后期由 letter_baicat 加。

minis_url: minis://skills/baicat/STYLES.md
