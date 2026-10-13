# 惠惠桌宠 · Megumin Desktop Pet

[![Code License: MIT](https://img.shields.io/badge/Code%20License-MIT-blue.svg)](LICENSE)

Windows Live2D 桌宠与桌面小助手，v20 完整运行资源和 EXE 现已公开，方便爱好者下载、研究和改进。非官方项目。

## 下载即用
从 [v20 完整发布](https://github.com/Explosion0v0/megumin-desktop-pet-open-source/releases/tag/v20) 下载 `MeguminPet-Live2D-v20.exe`，Windows 上双击运行，不需安装 Python。也可下载完整 ZIP 或含素材的源码 ZIP。
新电脑默认使用无需 API 的本地小助手；联网 AI 问答请在“AI 设置”填写**你自己的**接口、模型和 API Key。
发布文件不含作者的 API Key、私人接口配置、聊天记录或麦克风录音。个人配置仅保存在本机 `%APPDATA%/MeguminDesktopPet/`，不要上传。

## 功能
- 键盘/鼠标独立联动；键盘手限制自然可达距离，范围外按键不再拉长手臂。
- 圆角尾巴气泡：短文自适应大小，长文滚动查看，右键查看/复制全文。
- 半屏爆裂演出、彩色十字光粒、原有十种咏唱音效。
- 惠惠性格提示、文字 AI 对话、日语语音/中文字幕及开关式麦克风输入。
- 日常问候和预生成语音；本地歌曲播放、暂停、跳转、音量与嘴型联动。
- 网易云通过官方网页入口；不提供账号 Cookie，不解密 NCM，不包含歌曲。

## 日语语音与麦克风
原声咏唱和预生成日语短句随运行素材提供，**AI 对话的动态日语语音仍需自行配置本地 GPT-SoVITS 后端与声音权重**，不会仅凭聊天 API Key 自动具备完整语音推理环境。
后端接入代码见 [VOICE_BACKEND](docs/VOICE_BACKEND.md)。语音模型权重、参考录音和 GPU 环境不在本仓库；请根据自己的授权准备。
中文离线语音识别资源已包含。麦克风默认关闭，只有用户手动开启才采集；关闭释放设备。

## 源码运行与打包（Windows / PowerShell）
```powershell
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe .\app.py --self-test
& .\.venv\Scripts\python.exe .\tools\check_assets.py
& .\.venv\Scripts\python.exe .\app.py
& .\build.ps1
```
模型资源已放在 `assets/`；动作/参数映射针对当前角色，不保证任意其他模型即插即用。没有 Cubism `.cmo3` 原工程。

## 许可范围（重要）
**自有代码、原创动作和粒子参数采用 [MIT](LICENSE)，不表示所有随附资源均为 MIT 或自由开源素材。**
惠惠/逗之助形象、游戏 Live2D 模型、官方图片、声优录音、生成声音、Live2D Cubism Core 及外部模型权重保留各自权利/条款，不能由作者重新授权。来源仓库公开可下载不等于获得再分发或商业许可。
随附来源与条款见 [第三方声明](THIRD_PARTY_NOTICES.md)、[素材说明](docs/ASSETS.md)、`素材来源.txt` 和 `开源许可/`。本项目未取得角色素材通用再分发/商用许可；请在使用、二次发布或商业化前核实授权。权利方有异议可联系仓库维护者处理。

欢迎 Issue/PR。不要提交密钥、个人配置、私人聊天、录音、歌曲或未获授权的新增素材。见 [贡献指南](CONTRIBUTING.md)。
[更新日志](CHANGELOG.md) · [验证范围](docs/VERIFICATION.md)
