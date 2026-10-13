# 惠惠桌宠 · Megumin Desktop Pet

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Windows Live2D 桌宠与桌面小助手的 **v20 开源代码**。非官方项目，不代表《为美好的世界献上祝福！》及相关权利方。

## 当前功能
- 键盘/鼠标独立联动；键盘手限制自然可达距离，范围外按键不再拉长手臂。
- 圆角、带小尾巴的台词气泡，短文自动缩放，长文可滚动到末尾。
- 半屏爆裂演出与彩色十字光粒；原声播放逻辑保留，但不提供录音文件。
- 文本 AI 问答、日语回复/中文字幕与可开关麦克风输入。
- 本地歌曲播放、暂停、跳转、音量、嘴型联动。
- 网易云仅通过官方网页入口，不读取账号 Cookie 或解密 NCM。

## 重要：这是源码版，不是含角色资源的整合包
**仓库和公开 Release 不包含游戏 Live2D 模型、官方原画/图标、动漫原声、克隆语音、训练权重或歌曲。**
克隆代码后可进行状态机自测；完整 GUI 运行与 EXE 构建需要自备有权使用的运行素材，目录和检查方法见 [素材配置](docs/ASSETS.md)。
当前动作与参数映射针对原桌宠模型结构；不同 Live2D 模型需修改映射，不能保证任意模型即插即用。
原私人项目备份继续保持私有，不要求公众登录或获取其中的资源。

## 环境与运行（Windows / PowerShell）
```powershell
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
# 不需角色素材的状态机自测
& .\.venv\Scripts\python.exe .\app.py --self-test
# 自备素材检查；缺失时退出码为 2，并列出路径
& .\.venv\Scripts\python.exe .\tools\check_assets.py
# 素材齐全后再启动
& .\.venv\Scripts\python.exe .\app.py
# 打包结果在 dist/
& .\build.ps1
```
API Key 请在应用“AI 设置”中自行配置，不写进源码、Issue 或提交记录。
麦克风默认关闭，只有用户手动开启才采集；关闭开关释放设备。
应用运行配置保存在本机 `%APPDATA%/MeguminDesktopPet/`，不在 Git 仓库。

## 可选日语语音后端
`backend/` 提供本地 GPT-SoVITS v2ProPlus 接口代码，不提供权重或声优参考录音。
自行按 GPT-SoVITS 官方说明准备 GPU 推理环境；环境变量与配置说明见 [语音后端](docs/VOICE_BACKEND.md)。
声音模型与素材的授权不由本项目 MIT 许可证授予。

## 许可与贡献
本项目自有代码及原创动作/粒子参数采用 [MIT](LICENSE)。第三方依赖保持各自条款，见 [第三方声明](THIRD_PARTY_NOTICES.md)。
MIT 不覆盖惠惠/逗之助角色形象、游戏模型、声优表演、Live2D Cubism Core 或外部模型权重。
欢迎提交不含密钥、私人聊天记录和受限素材的 Issue/PR；见 [贡献指南](CONTRIBUTING.md)。

[更新日志](CHANGELOG.md) · [验证范围](docs/VERIFICATION.md)
