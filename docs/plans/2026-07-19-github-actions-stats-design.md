# GitHub Actions 统计卡 设计说明

## 背景与目标

在现有粉色 Profile README 上，对齐 Railgun19457：用 Actions 定时生成本地 SVG（stats / top-langs / streak / trophy），实现 stars、commits 等状态的准实时更新。

## 推荐方案

增强版：四张本地卡片 + 每日 cron + 手动 workflow_dispatch；README 引用 `./profile/*.svg`。

## 详细设计

- Workflow：`.github/workflows/update-stats.yml`
- 输出：`profile/stats.svg`、`top-langs.svg`、`streak.svg`、`trophy.svg`
- Secret：`PAT_TOKEN`（推送后由用户在 GitHub 网页配置）
