from .log_utils import AgentLog
import os
# LangChain追加
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain

def analyze_emotion(transcript: str, chunk: int = None):
    # LangChain LLMとプロンプトテンプレート
    llm = ChatOpenAI(openai_api_key=os.getenv("OPENAI_API_KEY"), model="gpt-3.5-turbo")
    prompt = PromptTemplate(
        template="""
        以下は商談の書き起こしテキストです。
        相手のテンション（高い・普通・低いなど）と、興味を持った話題やキーワードを日本語で簡潔に推定してください。
        ---
        {transcript}
        ---
        出力例: テンション: 高い, 興味: AI, DX, 自動化
        """,
        input_variables=["transcript"]
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    ai_output = chain.run({"transcript": transcript}).strip()
    thought = (
        f"【AI思考ログ】LangChain LLMChainで感情分析:\nプロンプト: {prompt.format(transcript=transcript)}\nAIの出力: {ai_output}"
    )
    print(thought)
    conclusion = ai_output
    log = AgentLog(
        agent_name="EmotionAgent",
        thought=thought,
        conclusion=conclusion,
        chunk=chunk,
        prompt=prompt.template,
        response=ai_output,
        status="done"
    )
    return conclusion, log
