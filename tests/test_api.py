from agents.llm_client import call_llm


result = call_llm(
    "你是一个助手",
    "请介绍一下理想汽车"
)


print("模型返回内容：")
print(result)python -m pip show openai