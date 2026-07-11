import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


def call_llm(system_prompt, user_content):

    try:

        response = client.chat.completions.create(

            # 根据你的DeepSeek账号实际可用模型调整
            model="deepseek-v4-flash",

            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],

            temperature=0.2,

            # V4支持更长输出
            max_tokens=64000,

            response_format={
                "type": "json_object"
            },

            stream=False
        )


        if not response.choices:
            print("LLM返回为空")
            return None


        content = response.choices[0].message.content


        print("======================")
        print("DeepSeek调用完成")
        print(
            "finish_reason:",
            response.choices[0].finish_reason
        )

        if response.usage:
            print(
                "Token:",
                response.usage.prompt_tokens,
                response.usage.completion_tokens
            )

        print("======================")


        return content


    except Exception as e:

        print("======================")
        print("调用DeepSeek失败")
        print(e)
        print("======================")


        return None