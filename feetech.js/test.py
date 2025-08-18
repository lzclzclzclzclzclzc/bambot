from flask import Flask, request, jsonify
from openai import OpenAI  
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 初始化 OpenAI 客户端（DeepSeek 配置）
client = OpenAI(
    api_key="YOUR_API_KEY",  # 替换为你的 DeepSeek API 密钥
    base_url="https://api.deepseek.com"
)

def prompt_to_json(user_prompt, positions=None):
    positions_text = ""
    if positions:
        positions_text = "当前所有电机位置如下：\n"
        for id, pos in positions.items():
            positions_text += f"ID {id}: {pos}\n"

    system_prompt = (
        "你是一个机器人学和自然语言处理专家，任务是将自然语言指令转换为用于控制Feetech伺服电机的JSON文件。机器人为一个带夹子的机械臂，结构与人类手臂类似。关节ID和对应描述如下：\n"
        "**右臂**：控制大臂在水平面转动 (ID: 1), 控制大臂在垂直面转动 (ID: 2), 控制肘关节在垂直面转动 (ID: 3), 控制手腕在垂直面转动 (ID: 4), 控制手腕旋转 (ID: 5), 控制夹子开闭 (ID: 6)\n"
        "**伺服详情**：\n"
        "- **手臂关节**：工作在位置模式（Mode 0）。位置范围为0–4095，对应0–360°。默认位置为180°（约2048）。角度转换为位置：position = (angle / 360) * 4095。\n"
        "- **特殊关节运动范围**：(ID: 6)position 2023为夹子闭合，position 3492为夹子完全打开；(ID: 1)position 761为左极限，position 3478为右极限。\n"
        "- **时间**：若未指定时间，假设动作按顺序发生，每动作间隔500ms。若指定时间（如“右臂在2秒内转到90°”），则使用指定时间。\n\n"
        f"{positions_text}"
        "**任务**：\n"
        "1. 解析自然语言指令（如“将右臂移到90°，左肘到45°，左轮以半速向前转”）。如遇到复合动作指令，先将动作按照电机的工作方式拆解成若干分解动作。\n"
        "2. 将术语如“右臂”映射到R_Rotation (ID: 1)， “左肘”映射到L_Elbow (ID: 9)等。\n"
        "3. 将手臂关节的角度转换为位置。对于轮子，将“向前”解释为正速度（如半速为1250）， “向后”为负速度，“停止”为0。\n"
        "4. 生成以下格式的JSON文件：\n"
        "[\n"
        "  { \"timestamp\": 0, \"actions\": [ { \"servoId\": <id>, \"position\": <value> }, ... ] },\n"
        "  { \"timestamp\": <ms>, \"actions\": [ { \"servoId\": <id>, \"position\": <value> }, ... ] },\n"
        "  ...\n"
        "]\n\n"
        "**要求**：\n"
        "- 仅输出json文件内容，json文件不要写任何注释。确保json格式正确且可解析。每个动作的时间戳应反映动作发生的顺序和指定的时间间隔。"
        "- 除json文件外不要任何解释或额外文本。\n\n"
        "用户自然语言指令为：" + user_prompt
    )

    try:
        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"API调用失败: {str(e)}")

@app.route("/generate_json", methods=["POST"])
def generate_json():
    user_prompt = request.json.get("prompt", "")
    positions = request.json.get("positions", None)
    try:
        json_str = prompt_to_json(user_prompt, positions)
        return jsonify({"json": json_str})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000)