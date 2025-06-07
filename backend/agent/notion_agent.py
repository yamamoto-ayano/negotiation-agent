from .log_utils import AgentLog
import openai
import os
from notion_client import Client
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain

def propose_from_notion(transcript: str, emotion_result: str, company_result: str, company_name: str, chunk: int = None):
    openai_api_key = os.getenv("OPENAI_API_KEY")
    notion = Client(auth=os.getenv("NOTION_API_KEY"))
    dify_db_id = "1813ace1838e8025909beb861f5972b2"
    output_db_id = "17c3ace1838e80208a52f27f31240cea"
    llm = ChatOpenAI(openai_api_key=openai_api_key, model="gpt-4o-mini")

    # 1. 検索条件自動生成
    prompt_search = PromptTemplate(
        template="""
        商談テキスト: {transcript}
        相手のテンション・興味: {emotion_result}
        会社情報: {company_result}
        上記をもとに、Dify事例DBを検索するための最適なキーワードを3つ日本語で出力してください。
        """,
        input_variables=["transcript", "emotion_result", "company_result"]
    )
    search_chain = LLMChain(llm=llm, prompt=prompt_search)
    keywords_raw = search_chain.run({
        "transcript": transcript,
        "emotion_result": emotion_result,
        "company_result": company_result
    }).strip()
    keywords = keywords_raw.replace("キーワード:", "").replace("・", "").replace("、", ",").split(",")
    keywords = [k.strip() for k in keywords if k.strip()]

    # 2. Dify事例DBから事例検索
    found_cases = []
    for kw in keywords:
        response = notion.databases.query(
            database_id=dify_db_id,
            filter={
                "property": "Name",
                "rich_text": {"contains": kw}
            }
        )
        for r in response["results"]:
            title = r["properties"]["Name"]["title"][0]["plain_text"]
            found_cases.append(title)
    found_cases = list(set(found_cases))

    # 3. 各エージェントの提案生成
    proposals = []
    proposal_prompts = []
    proposal_responses = []
    for agent, context in [
        ("テンション・興味エージェント", emotion_result),
        ("Dify事例エージェント", f"ヒット事例: {found_cases}"),
        ("会社情報エージェント", company_result)
    ]:
        prompt_proposal = PromptTemplate(
            template="""
            商談内容: {transcript}
            {agent}の観点: {context}
            上記を踏まえ、どんな提案をすればよいか日本語で簡潔に提案文を出力してください。
            """,
            input_variables=["transcript", "agent", "context"]
        )
        proposal_chain = LLMChain(llm=llm, prompt=prompt_proposal)
        proposal_text = proposal_chain.run({
            "transcript": transcript,
            "agent": agent,
            "context": context
        }).strip()
        proposals.append(proposal_text)
        proposal_prompts.append(prompt_proposal.template)
        proposal_responses.append(proposal_text)

    # 4. 合議AIで最終提案決定
    prompt_final = PromptTemplate(
        template="""
        以下は3人のエージェントによる提案です。
        1. テンション・興味エージェント: {proposal1}
        2. Dify事例エージェント: {proposal2}
        3. 会社情報エージェント: {proposal3}
        この中から最も良い提案を1つ選び、その理由とともに日本語で出力してください。
        """,
        input_variables=["proposal1", "proposal2", "proposal3"]
    )
    final_chain = LLMChain(llm=llm, prompt=prompt_final)
    final_proposal = final_chain.run({
        "proposal1": proposals[0],
        "proposal2": proposals[1],
        "proposal3": proposals[2]
    }).strip()

    # 5. Notion出力（省略可）
    parent_page = notion.pages.create(
        parent={"database_id": output_db_id},
        properties={
            "企業名": {"title": [{"text": {"content": company_name}}]}
        }
    )
    parent_id = parent_page["id"]
    notion.blocks.children.append(
        block_id=parent_id,
        children=[{
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "議事録"}}]}
        }, {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": transcript}}]}
        }]
    )
    notion.blocks.children.append(
        block_id=parent_id,
        children=[{
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "提案"}}]}
        }, {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": final_proposal}}]}
        }]
    )

    # ログ
    thought = (
        f"【AI思考ログ】\n"
        f"1. 検索キーワード生成プロンプト: {prompt_search.template}\n"
        f"2. 生成キーワード: {keywords}\n"
        f"3. Difyヒット事例: {found_cases}\n"
        f"4. 各エージェント提案: {proposals}\n"
        f"5. 合議プロンプト: {prompt_final.template}\n"
        f"6. 最終提案: {final_proposal}"
    )
    print(thought)
    conclusion = f"最終提案: {final_proposal}\nヒット事例: {found_cases}"
    log = AgentLog(
        agent_name="NotionProposalAgent",
        thought=thought,
        conclusion=conclusion,
        chunk=chunk,
        prompt={
            "search": prompt_search.template,
            "proposal": proposal_prompts,
            "final": prompt_final.template
        },
        response={
            "search": keywords,
            "proposal": proposal_responses,
            "final": final_proposal
        },
        status="done",
        extra={
            "found_cases": found_cases
        }
    )
    return conclusion, log

def markdown_to_notion_blocks(md: str):
    """
    シンプルなMarkdown→Notionブロック変換（見出し・リスト・段落のみ対応）
    """
    blocks = []
    for line in md.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('### '):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:]}}]}
            })
        elif line.startswith('## '):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]}
            })
        elif line.startswith('# '):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}
            })
        elif line.startswith('- '):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}
            })
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}
            })
    return blocks

def propose_from_notion_aggregate(full_transcript: str, full_emotion: str, full_company: str, company_name: str):
    openai_api_key = os.getenv("OPENAI_API_KEY")
    notion = Client(auth=os.getenv("NOTION_API_KEY"))
    dify_db_id = "1813ace1838e8025909beb861f5972b2"
    output_db_id = "17c3ace1838e80208a52f27f31240cea"
    llm = ChatOpenAI(openai_api_key=openai_api_key, model="gpt-4o-mini")

    # 1. 重要ポイント要約
    prompt_summary = PromptTemplate(
        template="""
        以下は商談の全文書き起こしです。
        1. 商談の中で特に重要なポイントだけを要約してください。
        2. 何がどのように契約につながりそうか、相手の興味や課題感を踏まえて整理してください。
        出力は日本語で、見出しやリストを使ってください。
        ---
        {full_transcript}
        ---
        """,
        input_variables=["full_transcript"]
    )
    summary_chain = LLMChain(llm=llm, prompt=prompt_summary)
    minutes_summary = summary_chain.run({"full_transcript": full_transcript}).strip()

    # 2. 検索キーワード生成
    prompt_search = PromptTemplate(
        template="""
        商談要約: {minutes_summary}
        相手のテンション・興味: {full_emotion}
        会社情報: {full_company}
        上記をもとに、Dify事例DBを検索するための最適なキーワードを3つ日本語で出力してください。
        """,
        input_variables=["minutes_summary", "full_emotion", "full_company"]
    )
    search_chain = LLMChain(llm=llm, prompt=prompt_search)
    keywords_raw = search_chain.run({
        "minutes_summary": minutes_summary,
        "full_emotion": full_emotion,
        "full_company": full_company
    }).strip()
    keywords = keywords_raw.replace("キーワード:", "").replace("・", "").replace("、", ",").split(",")
    keywords = [k.strip() for k in keywords if k.strip()]

    # 3. Dify事例DBから事例検索
    found_cases = []
    for kw in keywords:
        response = notion.databases.query(
            database_id=dify_db_id,
            filter={
                "property": "Name",
                "rich_text": {"contains": kw}
            }
        )
        for r in response["results"]:
            title = r["properties"]["Name"]["title"][0]["plain_text"]
            found_cases.append(title)
    found_cases = list(set(found_cases))

    # 4. 提案生成
    prompt_proposal = PromptTemplate(
        template="""
        商談要約: {minutes_summary}
        会社情報: {full_company}
        過去の類似事例: {found_cases}
        上記を踏まえ、どんな提案をすればよいか日本語で見出し・リスト・引用などを使って分かりやすくまとめてください。
        """,
        input_variables=["minutes_summary", "full_company", "found_cases"]
    )
    proposal_chain = LLMChain(llm=llm, prompt=prompt_proposal)
    proposal = proposal_chain.run({
        "minutes_summary": minutes_summary,
        "full_company": full_company,
        "found_cases": found_cases
    }).strip()

    # 5. Notion出力（親ページの中にサブページを作成）
    parent_page = notion.pages.create(
        parent={"database_id": output_db_id},
        properties={
            "企業名": {"title": [{"text": {"content": company_name}}]}
        }
    )
    parent_id = parent_page["id"]
    # サブページ「LangChain提案書」を作成
    proposal_page = notion.pages.create(
        parent={"page_id": parent_id},
        properties={
            "title": [{"text": {"content": "LangChain提案書"}}]
        }
    )
    proposal_page_id = proposal_page["id"]
    summary_blocks = markdown_to_notion_blocks(f"## 議事録要約\n{minutes_summary}")
    cases_md = "\n".join([f"- {case}" for case in found_cases])
    cases_blocks = markdown_to_notion_blocks(f"## 過去の類似事例\n{cases_md}")
    proposal_blocks = markdown_to_notion_blocks(f"## 提案\n{proposal}")
    all_blocks = summary_blocks + cases_blocks + proposal_blocks
    notion.blocks.children.append(block_id=proposal_page_id, children=all_blocks)

    # ログ
    thought = (
        f"【AI思考ログ】\n"
        f"1. 要約プロンプト: {prompt_summary.template}\n"
        f"2. 要約結果: {minutes_summary}\n"
        f"3. 検索キーワード生成プロンプト: {prompt_search.template}\n"
        f"4. 生成キーワード: {keywords}\n"
        f"5. Difyヒット事例: {found_cases}\n"
        f"6. 提案プロンプト: {prompt_proposal.template}\n"
        f"7. 最終提案: {proposal}"
    )
    print(thought)
    conclusion = f"minutes_summary: {minutes_summary}\nproposal: {proposal}\nfound_cases: {found_cases}"
    log = AgentLog(
        agent_name="NotionProposalAgentAggregate",
        thought=thought,
        conclusion=conclusion,
        chunk=None,
        prompt={
            "summary": prompt_summary.template,
            "search": prompt_search.template,
            "proposal": prompt_proposal.template
        },
        response={
            "summary": minutes_summary,
            "search": keywords,
            "proposal": proposal
        },
        status="done",
        extra={
            "found_cases": found_cases
        }
    )
    return {"minutes_summary": minutes_summary, "proposal": proposal, "found_cases": found_cases}, log
