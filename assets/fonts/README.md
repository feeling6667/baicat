# baicat 旁白字体目录

本目录存放 baicat 旁白（图上文字）使用的字体文件。

## 当前字体：乐米蜡笔体（LemiLaBiTi Regular）

- 文件名：`LemiLaBiTi-Regular.ttf`（字体内名 `LemiLaBiTi / Regular`，SHA-256 `85c4ba3b4c2e07673133f2b03e4557aec92dd6f75fa1b32c7de94d470cfd8c14`）
- 体积：约 11.5 MB，字符覆盖：简体中文常用字基本齐全（缺字会在落字时逐字报错，不会画豆腐块）
- 风格：儿童蜡笔涂鸦质感手写体——圆润、笔触松、偏童趣，契合影视图文故事的旁白气质
- 授权：**个人与企业均可免费商用**（见同目录 `乐米蜡笔体-授权说明.txt`；原始分发见猫啃网 https://www.maoken.com ）
- 下载来源（2026-10-13 获取）：猫啃网字体页 https://www.maoken.com/freefonts/27496.html → 下载包内 `乐米蜡笔体/乐米蜡笔体.ttf`

## 为什么字体文件不进 git

字体是第三方大体积二进制，为避免仓库膨胀，`.gitignore` 忽略 `assets/fonts/*.ttf`。
换机器/重装本 skill 后，若字体缺失：

1. 按上面的来源重新下载，重命名为 `LemiLaBiTi-Regular.ttf` 放回本目录；或
2. 放到共享目录 `/var/minis/shared/fonts/LemiLaBiTi-Regular.ttf`（脚本的第二搜索位）；或
3. 用 `letter_baicat.py --font <任意中文ttf>` 临时指定别的字体。

字体缺失时 `letter_baicat.py` 会**明确警告并回退到 Noto Sans CJK 黑体**，不会静默出别的字。

## 字体生效的两条路线

1. **生图自带字**（默认 `text_in_image: true`）：文字由生图模型画进留白区，prompt 里已写明
   “乐米蜡笔体式儿童蜡笔手写体”的风格描述——模型只能仿其笔感，字形不保证逐字一致。
2. **确定性加字**（`--no-text-in-image` 出无字底图，再跑 `letter_baicat.py --auto`）：
   用本目录的真实字体文件逐个字形绘制，字形 100% 准确、可复现——**要“真·乐米蜡笔体”走这条**。
