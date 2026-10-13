# 许可范围与第三方声明
根目录 LICENSE 的 MIT 只授权本项目自有代码、原创动作/粒子参数和原创提示文档，不替代第三方条款。

## 随附资源（非全部 MIT）
- `assets/models/megumin*`：Fantastic Days 游戏 Live2D 资源，来源 https://github.com/HaiKonofanDesu/konofan-live2d （实际下载来源以素材来源.txt 为准）。角色/游戏资源权利仍归相关权利方，来源仓库公开不能视为通用再分发/商用许可。
- 官方惠惠头像/图标与逗之助图片：来源、原版权标记见 `素材来源.txt`，不得重标 MIT。
- `assets/voices` 原始十种咏唱：来源 https://github.com/pcrbot/Explosion 的 1.0 资源包；未使用其插件代码，保留附带 AGPL 文本。该代码许可不另授予声优表演、动漫对白、音乐或音效权利。
- `assets/voices/generated`：本地 GPT-SoVITS 生成的日语短句，并非声优新录音。用户声音模型附带非商业/学习交流说明见 `开源许可/用户语音模型附带说明.txt`；权重与参考录音本身没有随附。
- Vosk 小模型、运行库按各自条款处理，附带来源/许可文本；不重新标 MIT。

本项目未取得角色素材通用再分发或商业授权，公开项目不代表官方认可，也不保证任何用途均获许可。使用/二次发布须核实相关权利。

## 软件依赖
PySide6/Qt：LGPLv3 或相应 Qt 条款；live2d-py：MIT 包装层；Live2D Cubism SDK/Core：分别有 Open Software / Proprietary 条款；PyOpenGL、Pillow、NumPy、Vosk 等遵循原许可。
PyInstaller 遵循 GPL/bootloader 例外；可选 GPT-SoVITS 后端及模型/组件各有许可。
完整许可副本位于 `开源许可/` 与 `third_party_licenses/`。构建/再分发请保留声明，并满足实际依赖版本要求（例如 Qt 的 LGPL 义务），不可改标成统一 MIT。
Live2D：https://www.live2d.com/en/sdk/license/
Qt：https://www.qt.io/licensing/open-source-lgpl-obligations
Vosk：https://alphacephei.com/vosk/models
