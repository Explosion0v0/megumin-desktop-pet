# 自备运行素材
本项目不下载、捆绑或重新授权动漫/游戏角色素材。请只使用你有权使用的文件。

在仓库根目录 `assets/` 放置：
- `models/megumin/Character.model3.json` 及其引用的 `.moc3`、纹理、动作/物理等文件。
- `models/megumin-eyepatch/Character.model3.json` 及对应引用文件。
- `chomusuke-official-profile.png`：当前运行代码按原图版式裁取角色区域；替代图片需调整绘制区域。
- `icon.ico`：自行准备的程序图标。
- `voices/manifest.json`：当前 VoicePlayer 的语音索引。其 chants/full/short 等结构须与播放代码一致；音频文件只在你有权使用时自备。
- 可选：`voices/generated/manifest.json` 与本地生成语音。
- 可选麦克风识别：`speech/vosk-model-small-cn-0.22/`；按 Vosk 官方模型说明下载并核对其许可。

仓库已提供原创 `choreography/DeskPet_Explosion.motion3.json` 和桌宠角色提示文档。
运行 `python tools/check_assets.py` 检查核心文件与模型引用。它不自动下载任何资源，也不把本机素材加入 Git。
启用语音、麦克风等可选功能还需要相应音频和识别资源；核心检查通过不等于所有可选功能准备完成。
换用其他角色模型须调整 `live_character.py` 的参数/部件映射。代码开源不等于原角色素材获得分发许可。
