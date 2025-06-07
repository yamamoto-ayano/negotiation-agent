from .log_utils import AgentLog
import os
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain

def estimate_budget(company_name: str, chunk: int = None):
    llm = ChatOpenAI(openai_api_key=os.getenv("OPENAI_API_KEY"), model="gpt-3.5-turbo")
    prompt = PromptTemplate(
        template="""
        会社名: {company_name}
        上記の会社の業種、従業員数、IT案件の予算感を日本語で簡潔に推定してください。
        出力例: 業種: IT, 従業員数: 200名, 予算: 500〜1000万円
        """,
        input_variables=["company_name"]
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    ai_output = chain.run({"company_name": company_name}).strip()
    thought = (
        f"【AI思考ログ】LangChain LLMChainで会社情報推定:\nプロンプト: {prompt.format(company_name=company_name)}\nAIの出力: {ai_output}"
    )
    print(thought)
    conclusion = ai_output
    log = AgentLog(
        agent_name="CompanyBudgetAgent",
        thought=thought,
        conclusion=conclusion,
        chunk=chunk,
        prompt=prompt.template,
        response=ai_output,
        status="done"
    )
    return conclusion, log
