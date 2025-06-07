from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from agent.emotion_agent import analyze_emotion
from agent.notion_agent import propose_from_notion, propose_from_notion_aggregate
from agent.company_agent import estimate_budget
from agent.log_utils import AgentLog, collect_logs
from agent.audio_utils import split_audio
from typing import Dict, List
import openai
import os
from dotenv import load_dotenv
import tempfile

app = FastAPI()

load_dotenv()

def transcribe_audio_file(file_path: str) -> str:
    openai.api_key = os.getenv("OPENAI_API_KEY")
    with open(file_path, "rb") as f:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=f
        )
    return transcript.text

@app.post("/analyze")
async def analyze(
    audio: UploadFile = File(...),
    company_name: str = Form(...)
):
    # 1. 音声ファイルを一時保存
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    # 2. 音声分割
    chunk_paths = split_audio(tmp_path, chunk_length_sec=300)  # 5分ごと
    logs = []
    transcripts = []
    emotion_results = []
    company_results = []

    # 3. 分割ごとにWhisperで文字起こし＆AI分析
    for idx, chunk_path in enumerate(chunk_paths):
        chunk_num = idx + 1
        transcript = transcribe_audio_file(chunk_path)
        transcripts.append(transcript)
        # テンション・興味分析
        emotion_result, emotion_log = analyze_emotion(transcript, chunk=chunk_num)
        logs.append(emotion_log)
        emotion_results.append(emotion_result)
        # 会社情報推定
        company_result, company_log = estimate_budget(company_name, chunk=chunk_num)
        logs.append(company_log)
        company_results.append(company_result)

    # 4. 全体まとめてNotionに1ページ出力
    full_transcript = "\n".join(transcripts)
    full_emotion = " / ".join(emotion_results)
    full_company = company_results[-1] if company_results else ""
    notion_result, notion_log = propose_from_notion_aggregate(
        full_transcript, full_emotion, full_company, company_name
    )
    logs.append(notion_log)

    log_output = collect_logs(logs)
    ai_thoughts = [
        {
            "agent": log.agent_name,
            "thought": log.thought,
            "prompt": log.prompt,
            "response": log.response,
            "conclusion": log.conclusion
        }
        for log in logs
    ]
    return JSONResponse({
        "minutes": notion_result.get("minutes_summary", ""),
        "proposal": notion_result.get("proposal", ""),
        "logs": log_output,
        "ai_thoughts": ai_thoughts
    })
