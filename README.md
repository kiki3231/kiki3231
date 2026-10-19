把兴趣做成能跑起来的东西。公开的四件作品在下面。桌面游戏搭子用 Go 在写，仓库还没公开。

## 作品

**[word2gal](https://github.com/kiki3231/word2gal)**
把一段文字收成可以玩的视觉小说。

**[devibe](https://github.com/kiki3231/devibe)**
终端里的 Git 仪表盘，离线，不用配置。

**[Grecord](https://github.com/kiki3231/Grecord)**
给玩过的游戏留一份打卡。

**[cloudguard-spring-boot-starter](https://github.com/kiki3231/cloudguard-spring-boot-starter)**
用注解把限流、幂等、锁和熔断接进 Spring Boot。

环境上常用 Docker、Linux、MySQL、Redis 和 PostgreSQL。

## 近况

<p>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./profile/contrib-dark.svg" />
    <img alt="过去一年的贡献" src="./profile/contrib-light.svg" />
  </picture>
</p>

<p>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./profile/languages-dark.svg" />
    <img alt="公开仓库的语言" src="./profile/languages-light.svg" />
  </picture>
</p>

<p>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./profile/wakatime-dark.svg" />
    <img alt="近 7 天编码时长" src="./profile/wakatime-light.svg" />
  </picture>
</p>

贡献方块把未公开仓库里的提交也算进去了，不显示仓库名。语言按公开仓库的代码量。编码时长来自 WakaTime。三张图每 6 小时重画，图里写着生成时间。

<!--
维护说明（这段注释不会出现在个人主页上）

本次改动：去掉打字机、图标墙和已经失效的第三方统计图。贡献、语言、编码时长改由仓库内脚本绘制。

更新
- 工作流：.github/workflows/update-stats.yml
- 定时：每 6 小时一次，也可在 Actions 里手动运行 Update profile stats
- 本地试跑：设置 GH_TOKEN 或 PAT_TOKEN 后执行 python .github/scripts/generate_profile.py

密钥
- PAT_TOKEN：需要能读取你名下的仓库，包含未公开仓库。失效时工作流会改用 Actions 自带令牌，那种令牌看不到未公开仓库，脚本会保留上一版贡献图，避免把私有提交刷掉。
- WAKATIME_API_KEY：WakaTime 的 API Secret。缺失时保留上一版编码时长图。

强制只用公开数据重画：在工作流里设置 FORCE_PUBLIC=1。
-->
