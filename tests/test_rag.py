from agents.fact_agent import extract_facts
from agents.rag_agent import generate_rag


material = """
理想i6是一款中大型纯电SUV。

全国统一零售价249800元。

车长4950毫米，
轴距3000毫米。

两驱版CLTC续航720公里，
四驱版660公里。

支持5C超充，
10分钟补能500公里。

搭载理想AD Max高级辅助驾驶系统。
"""


# Step1

facts = extract_facts(material)


print("=====FACTS=====")

print(facts)



# Step2

rag = generate_rag(facts)


print("=====RAG=====")

print(rag)