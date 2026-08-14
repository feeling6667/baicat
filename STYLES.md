# baicat 故事画风配方库

每段是一个画风的生图 prompt 模板。`generate_story.py` 按风格名读取对应代码块，
原样提取、自动填充占位符，禁止手工缩写或同义改写。
配方改动只改本文件，不改脚本。

占位符说明：
- `【主体】`：单格画面场景描述（由故事脚本的 panel.scene 填入），必填。
- `【文字】`：要画进图里的中文文字（对话气泡台词 + 旁白字幕），由 panel.text 填入，必填。
  生图时必须把这段中文写进 prompt，让 GPT Image 2 把文字画在图里，而不是放在图外。

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
muted desaturated palette. Loose hand-drawn lines, pencil hatching for shadows,
no thick black outlines. Paper grain texture visible.
Color scheme: grey-blue, off-white, dark brown, warm yellow.
Quiet, lonely, restrained atmosphere with subtle hope.
Minimalist indoor background. Large negative space at top for hand-lettered Chinese text.

SCENE: 【主体】

TEXT IN IMAGE (draw these exact Chinese characters into the image, in speech bubbles or narration areas):
【文字】
All Chinese text must be clearly readable, hand-lettered in black, no garbled or fake characters.
```

约束：手写体文字是画面一部分；排线阴影而非色块；低饱和不鲜艳；中文必须清晰可读无乱码。
配方不锁定角色外貌——人物由故事内容决定，各格保持一致即可。
