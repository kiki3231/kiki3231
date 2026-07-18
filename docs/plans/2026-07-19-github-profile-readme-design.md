# GitHub Profile README 设计说明

## 背景与目标

为 GitHub 用户 `kiki3231` 创建个人主页专用仓库 README，风格参考 [NayukiChiba](https://github.com/NayukiChiba)，并叠加 [Railgun19457](https://github.com/Railgun19457) 的 About me 与 Github Statistics 区块。成功标准：打开 `https://github.com/kiki3231` 时展示粉色可爱系打字欢迎、中英 About me、指定技术栈图标、统计卡片与贡献图。

## 现状与约束

- 本地目录 `git-profile` 为空，需初始化 Git
- Profile 仓库名必须与用户名一致：`kiki3231`
- 显示昵称：`Ado1024`
- Markdown 内无法使用自定义 CSS 闪烁；用 `readme-typing-svg` 粉系配色 + 多行轮播近似

## 方案对比

### 方案一：贴近 Chiba 结构（推荐）
- 优点：结构清晰、易维护、与参考主页一致
- 缺点：可爱装饰相对克制

### 方案二：强化可爱装饰
- 优点：视觉更粉嫩
- 缺点：易显杂乱，第三方图床依赖多

### 方案三：极简粉
- 优点：加载快
- 缺点：缺少 Contribution，信息量不足

## 推荐方案

方案一：居中打字欢迎 → About me（中英）→ 技术栈 Devicon → Github Statistics → Github Contribution。

## 详细设计

### 架构
单文件 `README.md`，全部通过公开 SVG/图片服务渲染，无构建步骤。

### 关键组件
1. Typing SVG：粉系颜色，文案含 `Ado1024`
2. About me：四条中英对照 bullet
3. 技术栈：Java、Go、HTML、CSS、JS、TS、Vue、React、Python、Docker、Linux
4. Statistics：`github-readme-stats`，`username=kiki3231`，粉系主题
5. Contribution：贡献活动图，`username=kiki3231`

### 数据流 / 接口
浏览器请求第三方 SVG；无后端。

### 异常与边界处理
第三方服务不可用时对应区块空白，不影响其余 Markdown。

### 测试策略
本地预览 Markdown；推送后在 GitHub Profile 页目视确认。

## 风险与待确认项

- 推送远程需用户确认（本次先本地 init + commit）
- `activity.yumeko.site` 为他人自建服务，Contribution 改用通用服务以保证可用性
