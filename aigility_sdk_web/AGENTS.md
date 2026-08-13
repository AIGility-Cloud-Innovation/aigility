需求文档生成失败

-------

<scene_type>content-site</scene_type>

# UI 设计指南

## 1. 设计推导依据

- **参考意图**: Mood Reference —— 参考 LangChain 中文文档的左侧固定导航 + 顶部搜索栏 + 右侧正文的三栏文档布局气质，以及浅绿高亮、代码块浅色底、面包屑层级等视觉特征；品牌色与排版按本 SDK 文档语义重建。
- **核心情绪 / 应用类型**: 技术开发者文档站，追求清晰、克制、可检索、长时间阅读舒适。
- **独特记忆点**: 左侧导航当前项以柔绿色实底高亮 + 极细左侧色条，呼应 SDK "接入 / 集成" 的语义，形成稳定的方位锚点。

## 2. Art Direction

- **方向名**: 技术文档 · 克制清新
- **Design Style**: Swiss Minimalist 瑞士极简 + Soft Blocks 柔色块 —— 以排版秩序保证阅读效率，以极低饱和的绿色块承载导航激活与代码块背景，避免视觉噪音。
- **DNA 参数**: 圆角 subtle (`rounded-md`) / 阴影 none → subtle / 间距 standard (`gap-4` / `p-6`) / 字体方向 无衬线正文 + 等宽代码 / 装饰手法 细色条 + 柔色块高亮
- **应用类型**: Content（文档站）—— 左侧固定目录 + 顶部导航 + 右侧流动正文。

## 3. Color System

**色彩关系**: 纯白文档底 + 近墨灰正文 + 柔绿主色（低饱和、高明度）+ 同色系极浅高亮底 + 浅灰边框；代码块使用浅色冷灰底 + 深色语法高亮。
**配色设计理由**: 主色选用低饱和绿，表达"接入、成长、开发者友好"，同时比蓝色更有辨识度；大面积保持白与浅灰，确保长文阅读不累；accent 承担 hover / 选中浅底，primary 只用于当前导航项、链接、CTA 与少量品牌锚点。
**主色推导**: 从 SDK "集成 / 接入 / 构建" 语义出发，选取草木绿系；降低饱和度、提高明度，使其在文档场景中克制不抢内容，仅作为方位与交互信号。
**使用比例**: 70% 中性（白/浅灰/深灰文字）/ 25% 辅助（极浅绿高亮底、代码块底、分隔线）/ 5% primary（当前导航、链接、品牌标识）。

| 角色 | CSS 变量 | Tailwind Class | HSL 值 | 设计说明 |
|---|---|---|---|---|
| bg | `--background` | `bg-background` | hsl(0 0% 100%) | 页面与文档正文背景，纯白阅读底 |
| card | `--card` | `bg-card` | hsl(0 0% 100%) | 顶部导航、弹层、搜索结果卡片 |
| text | `--foreground` | `text-foreground` | hsl(220 13% 14%) | 标题与正文，近墨深灰 |
| textMuted | `--muted-foreground` | `text-muted-foreground` | hsl(218 11% 45%) | 辅助说明、元信息、面包屑弱项 |
| primary | `--primary` | `bg-primary` / `text-primary` | hsl(142 55% 36%) | 当前导航项文字、链接、品牌锚点、搜索高亮 |
| primaryForeground | `--primary-foreground` | `text-primary-foreground` | hsl(0 0% 100%) | primary 实底上的文字图标 |
| accent | `--accent` | `bg-accent` | hsl(140 40% 94%) | 导航 hover / 选中浅底、代码块背景、提示条底 |
| accentForeground | `--accent-foreground` | `text-accent-foreground` | hsl(142 55% 28%) | accent 上的文字与图标，深绿 |
| border | `--border` | `border-border` | hsl(220 13% 91%) | 分隔线、输入框边框、表格线、代码块边框 |

**语义色提示**:
- 成功（示例通过 / 安装成功）: bg `hsl(142 55% 92%)` / border `hsl(142 45% 70%)` / text `hsl(142 60% 24%)` —— 与 primary 同色系，饱和度对齐 ±10%。
- 警告（注意事项 / 弃用提示）: bg `hsl(42 90% 94%)` / border `hsl(42 80% 70%)` / text `hsl(32 75% 30%)` —— 暖黄琥珀，饱和度低于 primary。
- 错误（报错示例 / 异常）: bg `hsl(0 80% 96%)` / border `hsl(0 70% 78%)` / text `hsl(0 70% 35%)` —— 柔红，饱和度与 primary 对齐。

## 4. 字体与节奏

- **font-display**: Noto Sans SC —— 中文标题清晰现代，与技术文档专业感匹配。
- **font-body**: Noto Sans SC —— 长文阅读友好，笔画均匀，层级清晰。
- **代码字体**: IBM Plex Mono —— 等宽字体，代码块与行内代码统一使用，增强技术质感。
- **字号**: H1 text-3xl md:text-4xl；H2 text-2xl；H3 text-xl；body text-base（16px），行高 1.75；muted text-sm。
- **圆角**: 小到中 —— 卡片与按钮 `rounded-md`，代码块 `rounded-md`，搜索框 `rounded-full`，保持克制。

## 5. 全局布局契约

- **Reference Layout Use**: 参考 LangChain 中文文档的三栏结构（顶部导航 + 左侧固定目录 + 右侧正文），保留面包屑、当前章节高亮、代码块浅色底等布局节奏；视觉语言按本 SDK 语义重建。
- **Page / Section Order**: 顶部导航栏（Logo / 搜索 / 版本号）→ 左侧侧边栏（章节目录，支持多级折叠）→ 右侧正文区（面包屑 → H1 → 正文 → 代码块 → 表格 → 上一页/下一页）。
- **Standard Content Zone**: 正文区 `max-w-3xl` + `mx-auto`（阅读行长约 70-80 字）；整体页面布局为 `sidebar w-64 + main flex-1`，桌面端总宽度随视口扩展，正文不超 720px。
- **Shell / Frame Alignment**: 顶部导航全宽 sticky，左侧侧边栏固定高度独立滚动，正文区独立滚动；内容容器与框架各自独立，不对齐同一网格。
- **Padding & Rhythm**: 正文区 `px-4 md:px-8 py-10 md:py-14`；段落间距 `mb-6`；标题上间距大于下间距，形成视觉节段。
- **Full-bleed Zones**: 顶部导航栏与侧边栏为全高 / 全宽框架元素；正文区内代码块、表格、提示框不超出正文 max-width。
- **Local Narrowing**: 表单、API 参数表格可使用 `overflow-x-auto`；引用块、提示条在正文宽度内左右缩进。
- **Overflow Strategy**: 宽表格、长代码行横向滚动；代码块显示行号与复制按钮，超出部分 `overflow-x-auto`。
- **Flexibility Boundary**: 允许移动端侧边栏抽屉化、正文 padding 收窄、字号微降；不允许更改主色、圆角系统、正文行长与排版节奏。

## 6. 视觉与动效

- **装饰**: 左侧细色条 + 柔绿色块高亮；代码块顶部语言标签；表格细线分隔。
- **阴影/边界**: 轻 —— 顶部导航仅底部 1px 边 + 极轻阴影；侧边栏无阴影，靠右侧边线分隔；卡片与弹层 `shadow-sm`。
- **动效**: 克制 —— 锚点跳转平滑滚动；hover 状态 150ms 背景色过渡；搜索结果淡入；移动端侧边栏抽屉滑入。

## 7. 组件原则

- 按钮、输入框、菜单项必须具备 Default / Hover / Active / Focus-visible / Disabled 状态。
- 左侧导航：默认 text-foreground，hover 用 accent 浅底，active / current 用 accent 底 + primary 文字 + 左侧 3px primary 竖条。
- 代码块：浅色冷灰底（accent 偏冷调）、左上语言标签、右上复制按钮、左侧行号列、语法高亮深色系；hover 复制按钮显示描边。
- 表格：细线边框，斑马纹使用极浅 accent；表头文字略重。
- 搜索框：圆角胶囊、左侧放大镜图标、右侧快捷键提示（⌘K）；聚焦时边框变 primary。
- 空状态与加载态延续同一套柔和绿灰语言，不使用默认 loading spinner 样式。

## 8. Image Direction

- **Image Role**: 无强制图片需求 —— 文档站优先通过排版、代码块高亮、表格与层级建立视觉记忆点；Logo 与图标按品牌提供。
- **Image Art Direction**: 无强制图片需求；若需章节头图或装饰插图，应采用极简线稿风 + 单色绿，保持克制。
- **Image Prompt Keywords**: 无
- **Image Avoidance**: 避免通用科技感插图、商务人物素材、无意义渐变背景图；文档站以内容可读性为第一优先级。

## 9. Anti-patterns

- **Split personality**: 首页用一套色、内页换一套色；全站文档共享同一 primary / accent / border 系统。
- **Primary everywhere**: 主色同时出现在按钮、tab、图标、边框、链接、表格头；按 70-25-5 把 primary 收回到当前导航、链接与品牌锚点。
- **Code block noise**: 代码块使用深色高对比 + 强阴影 + 彩色边框；文档站代码块以浅色底 + 克制语法高亮为主，减少阅读疲劳。
- **Invisible focus**: 搜索框、导航项、复制按钮只有 hover 没有 focus-visible；所有可交互元素必须有可见键盘焦点。
- **Long line fatigue**: 正文区撑满视口，行长超过 90 字；保持正文 max-w-3xl，确保中文阅读舒适。
- **Status color clash**: 成功 / 警告 / 错误提示条饱和度过高，与整体克制感冲突；语义色饱和度与 primary 对齐 ±15%。