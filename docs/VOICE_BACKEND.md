# 可选本机日语回复
先准备自己的 GPT-SoVITS 推理环境、预训练依赖、合法角色权重与参考音频；本仓库不提供或下载这些内容。
GPU/PyTorch 安装按设备和 GPT-SoVITS 官方文档处理，桌宠 requirements.txt 不包含完整语音训练环境。

在启动桌宠/服务的环境中设置：
```powershell
$env:GPT_SOVITS_DIR='D:\Models\GPT-SoVITS'
$env:MEGUMIN_VOICE_MODEL_DIR='D:\Models\MyVoice'
# 可选覆盖：MEGUMIN_SOVITS_WEIGHTS、MEGUMIN_GPT_WEIGHTS
```
默认权重相对模型根目录为 `模型v2proplus/huihui-v2proplus.pth`、`模型v2proplus/huihui-v2proplus.ckpt`。
现有后端参考音频相对路径为 `参考音频/平和/要は最初のきっかけ作りだと思うのですよ.wav`；替换声音时同步修改参考路径及 prompt_text，不提供此录音。
在本机 `%APPDATA%/MeguminDesktopPet/speech-runtime-v16.json` 填写 python（推理环境 python.exe）和 script（本仓库 backend/pet_japanese_tts_server_v16.py）绝对路径。
v20 仍使用该 v16 服务接口。无需把上述配置、权重或任何 API Key 提交到仓库。
后端只监听本机接口；不要未经额外鉴权直接暴露到公网。
官方项目：https://github.com/RVC-Boss/GPT-SoVITS
