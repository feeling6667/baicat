# baicat 故事画风配方库

每段是一个画风的生图 prompt 模板。`generate_story.py` 按风格名读取对应代码块，
原样提取、自动填充 `【主体】` 占位符，禁止手工缩写或同义改写。
配方改动只改本文件，不改脚本。

占位符说明：
- `【主体】`：单格画面场景描述（由故事脚本的 panel.scene 填入），必填。

---

## doodle 涂鸦

```
Hand-drawn doodle comic style illustration.
Black and white rough ink line art on clean white background.
The ONLY color in the image is ONE bright red element.
Sketchy, trembling, casual ink lines with unfinished edges and spontaneous linework.
Minimalist Q-version character: big head small body, simple dot eyes, messy tousled hair.
Lots of white negative space, centered subject.
Diary-style emotional illustration, melancholic yet humorous mood.
No text, no speech bubbles, no words, no letters anywhere in the image.

SCENE: 【主体】
```

约束：禁止图中出现文字；每格只有一个红色元素；人物造型各格一致。

---

## colored-pencil 彩铅

```
A healing hand-drawn webcomic illustration with colored pencil and graphite texture,
muted desaturated palette. Short-haired woman, back view or front view, wearing oversized
blue shirt and dark pants, slender figure, calm expression with hint of sadness.
Minimalist indoor background: white wall, corner or window. Large negative space at top
for hand-lettered black Chinese text like diary narration. Loose hand-drawn lines, pencil
hatching for shadows, no thick black outlines. Paper grain texture visible.
Color scheme: grey-blue, off-white, dark brown, warm yellow.
Quiet, lonely, restrained atmosphere with subtle hope.

SCENE: 【主体】
```

约束：手写体文字是画面一部分（与涂鸦风格相反）；排线阴影而非色块；低饱和不鲜艳。
