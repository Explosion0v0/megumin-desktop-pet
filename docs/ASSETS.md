# v20 运行资源
当前仓库包含 `assets/models/megumin` 与 `megumin-eyepatch` 的 moc3、纹理、动作；官方逗之助图片及图标；十种爆裂咏唱、预生成日语短句；中文 Vosk 小模型；原创动作/角色提示文件。
`python tools/check_assets.py` 检查核心素材与模型引用，资源存在时退出 0，缺失时退出 2 并列出路径。不会自动下载。
原始模型不是 `.cmo3` 编辑工程。换角色需调整 `live_character.py` 参数/部件映射。动态日语语音的训练权重/参考录音不包含，见 VOICE_BACKEND.md。
没有歌曲、账号资料、用户录音或作者的 AI Key。
模型/图片/录音不属于 MIT 授权范围；公开资源的来源与权利说明见根目录 `素材来源.txt`、THIRD_PARTY_NOTICES.md 与 `开源许可/`。公开下载并不替代使用或再分发所需许可。
