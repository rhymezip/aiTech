from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models import User, Ders, Soru, Bildirim, OgrenciHoca
from schemas import SoruRequest, AiMessageRequest
from utils import encrypt_data, decrypt_data
from errors import get_error, ALL_ERRORS, LANG_NAMES, ERROR_MSGS
from datetime import datetime
import os
import json
import httpx
import re

router = APIRouter(prefix="/api", tags=["AI"])

API_KEY = os.getenv("API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
AI_MODEL = os.getenv("MODEL", "openai/gpt-oss-20b:free")
SECRET_KEY = os.getenv("SECRET_KEY", "b27a2885fc06b4c1057899a151d038a48b5f6cc98ae9148d173332579d9383d1")


def get_user_lang(user) -> str:
    return getattr(user, 'dil', None) or "tr"


def get_current_user_fast(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()), db: Session = Depends(get_db)):
    from jose import jwt
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        uid = int(payload["sub"])
    except:
        raise HTTPException(status_code=401, detail=get_error("invalid_token"))

    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=401, detail=get_error("user_not_found"))
    return user


async def call_openrouter(user_message, system_prompt="", temperature=0.7, max_tokens=1000, user_lang="tr"):
    if not API_KEY:
        return ERROR_MSGS.get(user_lang, ERROR_MSGS["tr"])["ai_no_key"]
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            messages = [{"role": "system", "content": system_prompt}]
            if isinstance(user_message, list):
                messages.extend(user_message)
            else:
                messages.append({"role": "user", "content": user_message})
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://aitech.app",
                    "X-Title": "AiTech",
                },
                json={
                    "model": AI_MODEL,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        error_msg = str(e)
        msgs = ERROR_MSGS.get(user_lang, ERROR_MSGS["tr"])
        if "401" in error_msg or "unauthorized" in error_msg.lower():
            return msgs["ai_unauthorized"]
        elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            return msgs["ai_timeout"]
        elif "422" in error_msg or "quota" in error_msg.lower():
            return msgs["ai_quota"]
        else:
            return msgs["ai_generic"]


ANALYSIS_PROMPTS = {
    "tr": {
        "intro": "Bir öğrencinin '{tema}' dersindeki davranışını analiz et.",
        "current_question": 'Şu anki sorusu: "{soru}"',
        "prev_label": "Bu dersteki önceki soruları",
        "total_label": "toplam",
        "prev_none": "Yok",
        "not_understood_signs": "Aşağıdaki kriterlere göre öğrencinin ANLAMADIĞINI gösteren işaretler:",
        "understood_signs": "ANLADIĞINI gösteren işaretler:",
        "output_json": "Sadece şu JSON'u döndür, başka hiçbir şey yazma:",
        "no_keyword": "Yok",
    },
    "en": {
        "intro": "Analyze a student's behavior in the '{tema}' lesson.",
        "current_question": 'Current question: "{soru}"',
        "prev_label": "Previous questions in this lesson",
        "total_label": "total",
        "prev_none": "None",
        "not_understood_signs": "Signs that the student did NOT understand:",
        "understood_signs": "Signs that the student UNDERSTOOD:",
        "output_json": "Return only this JSON, nothing else:",
        "no_keyword": "None",
    },
    "tk": {
        "intro": "Okuwçynyň '{tema}' dersindeki hereketini analiz et.",
        "current_question": 'Şu anky soragy: "{soru}"',
        "prev_label": "Bu dersdeki öňki soraglar",
        "total_label": "jemi",
        "prev_none": "Ýok",
        "not_understood_signs": "Okuwçynyň ANLAMADYGYNY nyşanlary:",
        "understood_signs": "OKUWÇYNYŇ ANLANDYGYNY nyşanlary:",
        "output_json": "Diňe şu JSON-i ýaz:",
        "no_keyword": "Ýok",
    },
    "zh": {
        "intro": "分析学生在'{tema}'课程中的行为。",
        "current_question": '当前问题："{soru}"',
        "prev_label": "本课之前的提问",
        "total_label": "共计",
        "prev_none": "无",
        "not_understood_signs": "学生不理解的迹象：",
        "understood_signs": "学生理解的迹象：",
        "output_json": "只返回此JSON：",
        "no_keyword": "无",
    },
    "ko": {
        "intro": "'{tema}' 수업에서 학생의 행동을 분석하세요.",
        "current_question": '현재 질문: "{soru}"',
        "prev_label": "이 수업의 이전 질문",
        "total_label": "전체",
        "prev_none": "없음",
        "not_understood_signs": "학생이 이해하지 못함을 나타내는 표시:",
        "understood_signs": "학생이 이해한 표시:",
        "output_json": "이 JSON만 반환:",
        "no_keyword": "없음",
    },
    "ja": {
        "intro": "学生の一'{tema}'授業での行動を分析します。",
        "current_question": '現在の質問: "{soru}"',
        "prev_label": "この授業の以前の質問",
        "total_label": "合計",
        "prev_none": "なし",
        "not_understood_signs": "学生が表示し理解していない兆候:",
        "understood_signs": "学生が表示し理解した兆候:",
        "output_json": "このJSONのみを返し:",
        "no_keyword": "なし",
    },
    "pt": {
        "intro": "Analise o comportamento do aluno na aula '{tema}'.",
        "current_question": 'Pergunta atual: "{soru}"',
        "prev_label": "Perguntas anteriores desta aula",
        "total_label": "total",
        "prev_none": "Nenhuma",
        "not_understood_signs": "Sinais de que o aluno NÃO entendeu:",
        "understood_signs": "Sinais de que o aluno ENTENDEU:",
        "output_json": "Retorne apenas este JSON:",
        "no_keyword": "Nenhuma",
    },
    "ru": {
        "intro": "Проанализируйте поведение ученика на уроке '{tema}'.",
        "current_question": 'Текущий вопрос: "{soru}"',
        "prev_label": "Предыдущие вопросы на этом уроке",
        "total_label": "всего",
        "prev_none": "Нет",
        "not_understood_signs": "Признаки того, что студент НЕ ПОНЯЛ:",
        "understood_signs": "Признаки того, что студент ПОНЯЛ:",
        "output_json": "Верните только этот JSON:",
        "no_keyword": "Нет",
    },
    "fr": {
        "intro": "Analysez le comportement de l'élève dans le cours '{tema}'.",
        "current_question": 'Question actuelle: "{soru}"',
        "prev_label": "Questions précédentes de ce cours",
        "total_label": "total",
        "prev_none": "Aucune",
        "not_understood_signs": "Signes que l\'élève n\'a PAS compris:",
        "understood_signs": "Signes que l\'élève a COMPRIS:",
        "output_json": "Retournez uniquement ce JSON:",
        "no_keyword": "Aucune",
    },
}


STUDENT_AI_PROMPTS = {
    "tr": {
        "name": "AI Mentor",
        "greeting": "Merhaba {student_name}! 👋 {tema} konusunda sana yardımcı olmak için buradayım. Sorularını bekliyorum!",
        "system_intro": "Sen bir {lang_name} konuşan, sabırlı ve etkili bir eğitim AI asistanısın.",
        "task": "## Görevin\nÖğrenciye '{tema}' konusunu öğretmek.",
        "profile": "## Öğrenci Profili\n- İsim: {student_name} {student_surname}\n- Ders: {tema}\n- Bu dersteki toplam soru sayısı: {prev_count}\n- Tahmin edilen anlama seviyesi: {anlama_seviyesi}",
        "context": "## Bağlam\n{conv_context}Ders içeriği:\n{icerik}",
        "rules": "YANIT KURALLARI:\n- Sade, samimi, doğal bir dille yaz. Hiç markdown kullanma: yıldız (*), kare (#), tire listesi (-), tablo (|) gibi hiçbir formatlama karakteri kullanma.\n- Düz paragraf yaz.\n- Soru '{tema}' konusuyla tamamen alakasızsa, bunu dostane bir şekilde belirt ve konuya yönlendir. Alakalıysa veya öğrenci seninle sohbet ediyorsa normal konuş.\n- Uzun ve karmaşık cevaplar verme. Kısa, anlaşılır tut.\n- {lang_name} kullan.",
        "out_of_topic": "Bu soru şu an çalıştığımız '{tema}' konusundan biraz uzak. O konuyla ilgili bir şeyler sormak istersen yardımcı olmaktan memnuniyet duyarım.",
        "prev_conversation": "Önceki sorular ve cevaplar:",
        "question_prefix": "Soru",
        "answer_prefix": "Cevap",
    },
    "en": {
        "name": "AI Mentor",
        "greeting": "Hello {student_name}! 👋 I'm here to help you with {tema}. Feel free to ask your questions!",
        "system_intro": "You are a patient and effective educational AI assistant who speaks {lang_name}.",
        "task": "## Your Task\nTeach the student about '{tema}'.",
        "profile": "## Student Profile\n- Name: {student_name} {student_surname}\n- Lesson: {tema}\n- Total questions in this lesson: {prev_count}\n- Estimated understanding level: {anlama_seviyesi}",
        "context": "## Context\n{conv_context}Lesson content:\n{icerik}",
        "rules": "RESPONSE RULES:\n- Write in plain, natural, conversational language. No markdown: no asterisks (*), no hashes (#), no bullet dashes (-), no tables (|).\n- Write in plain paragraphs.\n- If the question is completely unrelated to '{tema}', mention it gently and redirect. If it's related or the student is just chatting, respond naturally.\n- Keep answers short and clear.\n- Use {lang_name}.",
        "out_of_topic": "That question is a bit outside our current topic of '{tema}'. Feel free to ask anything related to it!",
        "prev_conversation": "Previous questions and answers:",
        "question_prefix": "Question",
        "answer_prefix": "Answer",
    },
    "tk": {
        "name": "AI Mentor",
        "greeting": "Salam {student_name}! 👋 Men {tema} topicsynda size kömek etmek üçin dury. Soraglaryňyzy gözläýärin!",
        "system_intro": "Sen {lang_name} sözläşýän, sabyrly we täsirli bilim AI kömekçisiň.",
        "task": "## Wepalingyň\nOkuwçuya '{tema}' topicsyny öwretmek.",
        "profile": "## Okuwçy Profili\n- At: {student_name} {student_surname}\n- Ders: {tema}\n- Bu dersdeki jemi sorag: {prev_count}\n- Çenli düşünme derejesi: {anlama_seviyesi}",
        "context": "## Kontekst\n{conv_context}Ders mazmuny:\n{icerik}",
        "rules": "## Jogap Düzgünleri\n1. Soragy diýen ýaly oka\n2. Sorag '{tema}' bilen baglanyşykly dälsa: topicsyzdygyny aýdyň\n3. Gysga, açyk jogap beriň\n4. Okuwçu pikirlenmäge haýyň\n5. {lang_name} jogap beriň",
        "out_of_topic": "Bu sorag '{tema}' bilen baglanyşykly däl. Beýleki soraglaryňyza jogap bermäge begam.",
        "prev_conversation": "Öňki soraglar we jogaplar:",
        "question_prefix": "Sorag",
        "answer_prefix": "Jogap",
    },
    "zh": {
        "name": "AI导师",
        "greeting": "你好 {student_name}！👋 我来帮助你学习 {tema}。欢迎提问！",
        "system_intro": "你是一位说{lang_name}语的耐心而有效的教育AI助手。",
        "task": "## 你的任务\n教学生关于'{tema}'。",
        "profile": "## 学生档案\n- 姓名：{student_name} {student_surname}\n- 课程：{tema}\n- 本课问题总数：{prev_count}\n- 估计理解水平：{anlama_seviyesi}",
        "context": "## 上下文\n{conv_context}课程内容：\n{icerik}",
        "rules": "## 回复规则\n1. 仔细阅读问题\n2. 如果问题与'{tema}'无关：指出偏离主题\n3. 给出简短、清晰的答案\n4. 鼓励学生思考\n5. 使用{lang_name}回复",
        "out_of_topic": "这个问题与'{tema}'无关。我很乐意回答您的其他问题。",
        "prev_conversation": "之前的问答：",
        "question_prefix": "问题",
        "answer_prefix": "答案",
    },
    "ko": {
        "name": "AI 멘토",
        "greeting": "안녕하세요 {student_name}님! 👋 {tema} 주제를 도와드릴게요. 질문해 주세요!",
        "system_intro": "당신은 {lang_name}어를 사용하는 인내심 많고 효과적인 교육 AI 어시스턴트입니다.",
        "task": "## 당신의 임무\n학생에게 '{tema}' 주제를 가르치는 것입니다.",
        "profile": "## 학생 프로필\n- 이름: {student_name} {student_surname}\n- 수업: {tema}\n- 이 수업의 총 질문 수: {prev_count}\n- 추정 이해 수준: {anlama_seviyesi}",
        "context": "## 맥락\n{conv_context}수업 내용:\n{icerik}",
        "rules": "## 응답 규칙\n1. 질문을 주의 깊게 읽으세요\n2. 질문이 '{tema}'와 관련 없는 경우: 관련 없다고 명시하세요\n3. 짧고 명확한 답변을 제공하세요\n4. 학생이 생각하도록 격려하세요\n5. {lang_name}로 답변하세요",
        "out_of_topic": "이 질문은 '{tema}'와 관련이 없습니다. 다른 질문에 기꺼이 답변해 드리겠습니다.",
        "prev_conversation": "이전 질문과 답변:",
        "question_prefix": "질문",
        "answer_prefix": "답변",
    },
    "ja": {
        "name": "AIメンター",
        "greeting": "こんにちは {student_name}さん！👋 {tema}のトピックをサポートする準備ができています。質問をどうぞ！",
        "system_intro": "{lang_name}を話す、辛抱強く効果的な教育AIアシスタントです。",
        "task": "## あなたの任務\n学生に'{tema}'のトピックを教えること。",
        "profile": "## 学生プロフィール\n- 名前: {student_name} {student_surname}\n- 授業: {tema}\n- この授業の総質問数: {prev_count}\n- 推定理解レベル: {anlama_seviyesi}",
        "context": "## コンテキスト\n{conv_context}授業内容:\n{icerik}",
        "rules": "## 返信ルール\n1. 質問を注意深く読んでください\n2. 質問が'{tema}'と無関係な場合：無関係と明記してください\n3. 短く明確な回答をしてください\n4. 学生が考えるよう促してください\n5. {lang_name}で回答してください",
        "out_of_topic": "この質問は'{tema}'と関連がありません。他の質問にお答えします。",
        "prev_conversation": "過去の質問と回答:",
        "question_prefix": "質問",
        "answer_prefix": "回答",
    },
    "pt": {
        "name": "Mentor IA",
        "greeting": "Olá {student_name}! 👋 Estou aqui para ajudá-lo com {tema}. Sinta-se à vontade para fazer perguntas!",
        "system_intro": "Você é um assistente de educação IA paciente e eficaz que fala {lang_name}.",
        "task": "## Sua Tarefa\nEnsinar o aluno sobre '{tema}'.",
        "profile": "## Perfil do Aluno\n- Nome: {student_name} {student_surname}\n- Aula: {tema}\n- Total de perguntas nesta aula: {prev_count}\n- Nível de compreensão estimado: {anlama_seviyesi}",
        "context": "## Contexto\n{conv_context}Conteúdo da aula:\n{icerik}",
        "rules": "## Regras de Resposta\n1. Leia a pergunta com atenção\n2. Se a pergunta não for sobre '{tema}': indique que está fora do tópico\n3. Dê uma resposta curta e clara\n4. Incentive o aluno a pensar\n5. Responda em {lang_name}",
        "out_of_topic": "Esta pergunta não está relacionada a '{tema}'. Ficarei feliz em responder suas outras perguntas.",
        "prev_conversation": "Perguntas e respostas anteriores:",
        "question_prefix": "Pergunta",
        "answer_prefix": "Resposta",
    },
    "ru": {
        "name": "ИИ Наставник",
        "greeting": "Привет {student_name}! 👋 Я здесь, чтобы помочь вам с темой '{tema}'. Задавайте вопросы!",
        "system_intro": "Вы терпеливый и эффективный образовательный ИИ-ассистент, говорящий на {lang_name}.",
        "task": "## Ваша Задача\nОбучать студента теме '{tema}'.",
        "profile": "## Профиль Студента\n- Имя: {student_name} {student_surname}\n- Урок: {tema}\n- Всего вопросов в этом уроке: {prev_count}\n- Предполагаемый уровень понимания: {anlama_seviyesi}",
        "context": "## Контекст\n{conv_context}Содержание урока:\n{icerik}",
        "rules": "## Правила Ответа\n1. Внимательно прочитайте вопрос\n2. Если вопрос не относится к '{tema}': укажите, что он не по теме\n3. Дайте краткий и четкий ответ\n4. Побуждайте студента думать\n5. Отвечайте на {lang_name}",
        "out_of_topic": "Этот вопрос не связан с '{tema}'. Буду рад ответить на ваши другие вопросы.",
        "prev_conversation": "Предыдущие вопросы и ответы:",
        "question_prefix": "Вопрос",
        "answer_prefix": "Ответ",
    },
    "fr": {
        "name": "Mentor IA",
        "greeting": "Bonjour {student_name}! 👋 Je suis là pour vous aider avec le sujet '{tema}'. N'hésitez pas à poser vos questions!",
        "system_intro": "Vous êtes un assistant pédagogique IA patient et efficace qui parle {lang_name}.",
        "task": "## Votre Tâche\nEnseigner à l'élève le sujet '{tema}'.",
        "profile": "## Profil de l'Élève\n- Nom: {student_name} {student_surname}\n- Cours: {tema}\n- Nombre total de questions dans ce cours: {prev_count}\n- Niveau de compréhension estimé: {anlama_seviyesi}",
        "context": "## Contexte\n{conv_context}Contenu du cours:\n{icerik}",
        "rules": "## Règles de Réponse\n1. Lisez la question attentivement\n2. Si la question n'est pas liée à '{tema}': indiquez qu'elle est hors sujet\n3. Donnez une réponse courte et claire\n4. Encouragez l'élève à réfléchir\n5. Répondez en {lang_name}",
        "out_of_topic": "Cette question n'est pas liée à '{tema}'. Je serai heureux de répondre à vos autres questions.",
        "prev_conversation": "Questions et réponses précédentes:",
        "question_prefix": "Question",
        "answer_prefix": "Réponse",
    },
}


TEACHER_AI_PROMPTS = {
    "tr": {
        "name": "Eğitim Koçu",
        "greeting": "Merhaba {ad} {soyad}! 👋 Size yardımcı olmak için buradayım.",
        "intro": "Sen {ad} {soyad} adlı deneyimli öğretmenin eğitim AI asistanısın.",
        "task": "## Görevin\nDers planlaması, içerik üretimi, öğrenci analizi ve pedagojik destek sağlamak.",
        "profile": "## Öğretmen Profili\n- İsim: {ad} {soyad}\n- Tercih edilen dil: {lang_name}\n- Toplam öğrenci: {ogrenci_count}\n- Toplam ders: {ders_count}",
        "no_students": "Henüz öğrenci yok",
        "no_lessons": "henüz ders yok",
        "difficult_topics": "Zorlayıcı Konular",
        "no_data": "Henüz yeterli veri yok",
        "rules": "YANIT KURALLARI:\n- {lang_name} yanıt ver\n- Somut, pratik öneriler ver\n- Sade dil kullan, tablo veya karmaşık format kullanma\n- Örneklerle destekle",
        "request": "## Talep",
    },
    "en": {
        "name": "Education Coach",
        "greeting": "Hello {ad} {soyad}! 👋 I'm here to help you.",
        "intro": "You are the educational AI assistant of experienced teacher {ad} {soyad}.",
        "task": "## Your Task\nProvide lesson planning, content creation, student analysis and pedagogical support.",
        "profile": "## Teacher Profile\n- Name: {ad} {soyad}\n- Preferred language: {lang_name}\n- Total students: {ogrenci_count}\n- Total lessons: {ders_count}",
        "no_students": "No students yet",
        "no_lessons": "no lessons yet",
        "difficult_topics": "Difficult Topics",
        "no_data": "Not enough data yet",
        "rules": "RESPONSE RULES:\n- Respond in {lang_name}\n- Give concrete, practical suggestions\n- Use plain language, no tables or complex formatting\n- Support with examples",
        "request": "## Request",
    },
    "tk": {
        "name": "Bilim Koç",
        "greeting": "Salam {ad} {soyad}! 👋 Size kömek etmek üçin dury.",
        "intro": "Sen {ad} {soyad} adly tejribeli mugallımıň bilim AI kömekçisiň.",
        "task": "## Wepalingyň\nDers meýilnamalary, mazmun döretmek, okuwçı derwsindiriş we pedagogik goldaw bermek.",
        "profile": "## Mugallım Profili\n- At: {ad} {soyad}\n- Saýlanan dil: {lang_name}\n- Jemi okuwçy: {ogrenci_count}\n- Jemi ders: {ders_count}",
        "no_students": "Henüz okuwçy ýok",
        "no_lessons": "henüz ders ýok",
        "difficult_topics": "Kynlykly Meseleler",
        "no_data": "Henüz ýeterli maglumat ýok",
        "rules": "## Jogap Düzgünleri\n- {lang_name} jogap beriň\n- Konkret maslahatlar beriň\n- Markdown format ulanyň\n- Mysal bilen goldaň",
        "request": "## Talap",
    },
    "zh": {
        "name": "教育教练",
        "greeting": "你好 {ad} {soyad}！👋 我来帮助你。",
        "intro": "您是资深教师{ad} {soyad}的教育AI助手。",
        "task": "## 您的任务\n提供课程规划、内容创作、学生分析和教学支持。",
        "profile": "## 教师档案\n- 姓名：{ad} {soyad}\n- 首选语言：{lang_name}\n- 学生总数：{ogrenci_count}\n- 课程总数：{ders_count}",
        "no_students": "暂无学生",
        "no_lessons": "暂无课程",
        "difficult_topics": "难点主题",
        "no_data": "暂无足够数据",
        "rules": "## 回复规则\n- 使用{lang_name}回复\n- 给出具体建议\n- 使用Markdown格式\n- 用例子支持",
        "request": "## 请求",
    },
    "ko": {
        "name": "교육 코치",
        "greeting": "안녕하세요 {ad} {soyad}님! 👋 도움드릴게요.",
        "intro": "당신은 경험丰富的 교사 {ad} {soyad}의 교육 AI 어시스턴트입니다.",
        "task": "## 당신의 임무\n수업 계획, 콘텐츠 제작, 학생 분석 및 교육적 지원을 제공합니다.",
        "profile": "## 교사 프로필\n- 이름: {ad} {soyad}\n- 선호 언어: {lang_name}\n- 총 학생: {ogrenci_count}\n- 총 수업: {ders_count}",
        "no_students": "아직 학생이 없습니다",
        "no_lessons": "아직 수업이 없습니다",
        "difficult_topics": "어려운 주제",
        "no_data": "아직 충분한 데이터가 없습니다",
        "rules": "## 응답 규칙\n- {lang_name}로 응답하세요\n- 구체적인 제안을 하세요\n- Markdown 형식을 사용하세요\n- 예시로 지원하세요",
        "request": "## 요청",
    },
    "ja": {
        "name": "教育トレーナー",
        "greeting": "こんにちは {ad} {soyad}先生！👋 お手伝いします。",
        "intro": "あなたは経験丰富的先生{ad} {soyad}的教育AIアシスタントです。",
        "task": "## あなたの任務\n授業計画、コンテンツ作成、学生分析、教育的サポートを提供します。",
        "profile": "## 先生プロフィール\n- 名前: {ad} {soyad}\n- 優先言語: {lang_name}\n- 総学生数: {ogrenci_count}\n- 総授業数: {ders_count}",
        "no_students": "まだ学生がいません",
        "no_lessons": "まだ授業がありません",
        "difficult_topics": "難しいトピック",
        "no_data": "まだ十分なデータがありません",
        "rules": "## 返信ルール\n- {lang_name}で返信してください\n- 具体的な提案をしてください\n- Markdown形式を使用してください\n- 例でサポートしてください",
        "request": "## リクエスト",
    },
    "pt": {
        "name": "Treinador Educacional",
        "greeting": "Olá {ad} {soyad}! 👋 Estou aqui para ajudá-lo.",
        "intro": "Você é o assistente educacional de IA do professor experiente {ad} {soyad}.",
        "task": "## Sua Tarefa\nFornecer planejamento de aula, criação de conteúdo, análise de alunos e suporte pedagógico.",
        "profile": "## Perfil do Professor\n- Nome: {ad} {soyad}\n- Idioma preferido: {lang_name}\n- Total de alunos: {ogrenci_count}\n- Total de aulas: {ders_count}",
        "no_students": "Ainda não há alunos",
        "no_lessons": "ainda não há aulas",
        "difficult_topics": "Tópicos Difíceis",
        "no_data": "Ainda não há dados suficientes",
        "rules": "## Regras de Resposta\n- Responda em {lang_name}\n- Dê sugestões concretas\n- Use formato Markdown\n- Aplique com exemplos",
        "request": "## Pedido",
    },
    "ru": {
        "name": "Тренер по образованию",
        "greeting": "Привет {ad} {soyad}! 👋 Я здесь, чтобы помочь вам.",
        "intro": "Вы — образовательный ИИ-ассистент опытного уч��теля {ad} {soyad}.",
        "task": "## Ваша Задача\nОбеспечить планирование уроков, создание контента, анализ учеников и педагогическую поддержку.",
        "profile": "## Профиль Учителя\n- Имя: {ad} {soyad}\n- Предпочитаемый язык: {lang_name}\n- Всего учеников: {ogrenci_count}\n- Всего уроков: {ders_count}",
        "no_students": "Пока нет учеников",
        "no_lessons": "пока нет уроков",
        "difficult_topics": "Сложные Темы",
        "no_data": "Пока недостаточно данных",
        "rules": "## Правила Ответа\n- Отвечайте на {lang_name}\n- Давайте конкретные предложения\n- Используйте Markdown формат\n- Подкрепляйте примерами",
        "request": "## Запрос",
    },
    "fr": {
        "name": "Coach Éducatif",
        "greeting": "Bonjour {ad} {soyad}! 👋 Je suis là pour vous aider.",
        "intro": "Vous êtes l'assistant pédagogique IA du professeur expérimenté {ad} {soyad}.",
        "task": "## Votre Tâche\nFournir la planification des cours, la création de contenu, l'analyse des étudiants et le soutien pédagogique.",
        "profile": "## Profil de l'Enseignant\n- Nom: {ad} {soyad}\n- Langue préférée: {lang_name}\n- Total étudiants: {ogrenci_count}\n- Total cours: {ders_count}",
        "no_students": "Pas encore d'étudiants",
        "no_lessons": "pas encore de cours",
        "difficult_topics": "Sujets Difficiles",
        "no_data": "Pas encore assez de données",
        "rules": "## Règles de Réponse\n- Répondez en {lang_name}\n- Donnez des suggestions concrètes\n- Utilisez le format Markdown\n- Appuyez avec des exemples",
        "request": "## Demande",
    },
}


RULE_KEYWORDS = {
    "tr": {
        "not_understood": ["anlamadım", "anlayamıyorum", "hâlâ", "hala", "tekrar", "yine", "kafam karıştı", "karıştı", "bir türlü", "anlaşılmadı", "mantığını", "neden böyle", "nasıl oluyor"],
        "understood": ["teşekkür", "anladım", "tamam", "peki ya", "bunun dışında", "başka"]
    },
    "en": {
        "not_understood": ["dont understand", "cannot understand", "still", "again", "confused", "how does", "why", "not clear", "do not get", "struggling", "lost"],
        "understood": ["thank", "understood", "got it", "clear", "makes sense", "ok then"]
    },
    "tk": {
        "not_understood": ["anlamadym", "anlamadym", "hãlâ", "häli", "täzeden", "ýene", "kafam garişdy", "garişdy", "bir Türli", "düşündirmedi", "mantygy", "nähil bolýar"],
        "understood": ["teşekkür", "anladym", "okuw", "peki hem", "başga"]
    },
    "zh": {
        "not_understood": ["不懂", "不明白", "还是", "又", "confused", "怎么会", "为什么", "不清楚", "不知道"],
        "understood": ["谢谢", "明白了", "清楚了", "明白"]
    },
    "ko": {
        "not_understood": ["이해 못해", "모르겠어", "여전히", "다시", "어떻게", "왜", "헷갈려"],
        "understood": ["감사", "이해했어", "알겠어", "좋아"]
    },
    "ja": {
        "not_understood": ["わからない", "理解できない", "まだ", "また", "わからない", "なぜ", "混乱"],
        "understood": ["ありがとう", "理解した", "わかりました"]
    },
    "pt": {
        "not_understood": ["não entendo", "não compreendo", "ainda", "novamente", "confuso", "como funciona", "por que"],
        "understood": ["obrigado", "entendi", "claro"]
    },
    "ru": {
        "not_understood": ["не понимаю", "непонятно", "снова", "опять", "путаю", "как", "почему"],
        "understood": ["спасибо", "понял", "ясно"]
    },
    "fr": {
        "not_understood": ["ne comprends pas", "incertain", "encore", "encore", "confus", "comment", "pourquoi", "pas clair"],
        "understood": ["merci", "compris", "clair"]
    },
}


async def detect_understanding(soru: str, tema: str, prev_sorular: list, prev_count: int, user_lang: str = "tr"):
    prompts = ANALYSIS_PROMPTS.get(user_lang, ANALYSIS_PROMPTS["tr"])

    if not API_KEY:
        return _rule_based_detect(soru, prev_count, user_lang)

    onceki = "\n".join(f"- {s}" for s in prev_sorular) if prev_sorular else prompts["prev_none"]

    prompt = f"""{prompts['intro'].format(tema=tema)}
{prompts['current_question'].format(soru=soru)}
{prompts['prev_label']} ({prev_count} {prompts['total_label']}):
{onceki}
{prompts['not_understood_signs']}
- Various expressions indicating lack of understanding
- Repeating similar questions
- 4+ questions in this lesson
- Questions about basic concepts
{prompts['understood_signs']}
- First time asking about a topic
- Detail or application questions
- Curious follow-up questions
{prompts['output_json']}
{{"anlamadi": true}} veya {{"anlamadi": false}} veya {{"anlamadi": null}}"""

    raw = await call_openrouter(prompt, f"Return only JSON.", user_lang=user_lang)

    try:
        clean = re.sub(r"```[a-z]*|```", "", raw).strip()
        parsed = json.loads(clean)
        val = parsed.get("anlamadi")
        if val is True:
            return False
        if val is False:
            return True
        return None
    except:
        return _rule_based_detect(soru, prev_count, user_lang)


def _rule_based_detect(soru: str, prev_count: int, user_lang: str = "tr"):
    s = soru.lower()
    rules = RULE_KEYWORDS.get(user_lang, RULE_KEYWORDS["tr"])

    kotu = rules["not_understood"]
    iyi = rules["understood"]

    kotu_skor = sum(1 for k in kotu if k in s)
    iyi_skor = sum(1 for k in iyi if k in s)

    if kotu_skor > 0 or prev_count >= 4:
        return False
    if iyi_skor > 0:
        return True
    return None


def check_notification_threshold(db, ders_id, hoca_id):
    total = db.query(Soru).filter(Soru.ders_id == ders_id, Soru.anladi_mi != None).count()
    if total < 3:
        return
    anlamadi = db.query(Soru).filter(Soru.ders_id == ders_id, Soru.anladi_mi == False).count()
    yuzde = int(anlamadi / total * 100)
    if yuzde < 15:
        return

    ders = db.query(Ders).filter(Ders.id == ders_id).first()
    if not ders:
        return

    existing = db.query(Bildirim).filter(
        Bildirim.hoca_id == hoca_id,
        Bildirim.konu_encrypted == ders.tema_encrypted
    ).first()

    if existing:
        existing.yuzde = yuzde
        existing.goruldu = False
        existing.timestamp = datetime.utcnow()
    else:
        db.add(Bildirim(hoca_id=hoca_id, konu_encrypted=ders.tema_encrypted, yuzde=yuzde))
    db.commit()


@router.post("/students/ask")
async def ask_question(data: SoruRequest, db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)

    if cu.role != "student":
        raise HTTPException(status_code=403, detail=get_error("unauthorized", lang))

    lesson = db.query(Ders).filter(Ders.id == data.ders_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail=get_error("lesson_not_found", lang))

    relation = db.query(OgrenciHoca).filter(
        OgrenciHoca.ogrenci_id == cu.id,
        OgrenciHoca.hoca_id == lesson.hoca_id
    ).first()
    if not relation:
        raise HTTPException(status_code=403, detail=get_error("no_lesson_access", lang))

    tema = decrypt_data(lesson.tema_encrypted)
    icerik = decrypt_data(lesson.icerik_encrypted) if lesson.icerik_encrypted else ""

    prev_sorular = (
        db.query(Soru)
        .filter(Soru.ders_id == data.ders_id, Soru.ogrenci_id == cu.id)
        .order_by(Soru.timestamp.asc())
        .all()
    )
    prev_count = len(prev_sorular)

    conversation_history = []
    for s in prev_sorular:
        soru_text = decrypt_data(s.soru_encrypted)
        cevap_text = decrypt_data(s.ai_cevap_encrypted) if s.ai_cevap_encrypted else ""
        conversation_history.append({"soru": soru_text, "cevap": cevap_text})
    prev_texts = conversation_history[-10:] if conversation_history else []

    student_name = decrypt_data(cu.ad_encrypted) if getattr(cu, "ad_encrypted", None) else ""
    student_surname = decrypt_data(cu.soyad_encrypted) if getattr(cu, "soyad_encrypted", None) else ""
    user_lang = cu.dil or "tr"
    lang_name = LANG_NAMES.get(user_lang, "Türkçe")

    student_prompts = STUDENT_AI_PROMPTS.get(user_lang, STUDENT_AI_PROMPTS["tr"])

    conv_context = ""
    if prev_texts:
        conv_lines = []
        for i, msg in enumerate(prev_texts):
            conv_lines.append(f"{student_prompts['question_prefix']} {i+1}: {msg['soru']}")
            conv_lines.append(f"{student_prompts['answer_prefix']} {i+1}: {msg['cevap']}")
        conv_context = student_prompts['prev_conversation'] + "\n" + "\n".join(conv_lines) + "\n\n"

    anlama_seviyesi = "orta"
    if prev_count > 0:
        anladim_sayisi = sum(1 for s in prev_sorular if s.anladi_mi == True)
        anlamadim_sayisi = sum(1 for s in prev_sorular if s.anladi_mi == False)
        if anlamadim_sayisi > anladim_sayisi:
            anlama_seviyesi = "zayıf"
        elif anladim_sayisi > anlamadim_sayisi:
            anlama_seviyesi = "iyi"

    system_prompt = f"""{student_prompts['system_intro'].format(lang_name=lang_name)}
{student_prompts['task'].format(tema=tema)}
{student_prompts['profile'].format(student_name=student_name, student_surname=student_surname, tema=tema, prev_count=prev_count, anlama_seviyesi=anlama_seviyesi)}
{student_prompts['context'].format(conv_context=conv_context, icerik=icerik)}
{student_prompts['rules'].format(tema=tema, lang_name=lang_name)}

ÖNEMLI: Cevaplarında kesinlikle markdown formatlama kullanma. Yıldız (*), kare (#), alt çizgi (_), tire listesi, tablo gibi hiçbir karakter kullanma. Sadece düz, sade metin yaz. Sanki bir arkadaşına mesaj atıyormuş gibi doğal ve samimi bir dil kullan."""

    answer = await call_openrouter(data.soru, system_prompt, user_lang=user_lang)

    prev_questions = [msg['soru'] for msg in prev_texts]
    auto_anladi = await detect_understanding(
        soru=data.soru,
        tema=tema,
        prev_sorular=prev_questions,
        prev_count=prev_count,
        user_lang=user_lang,
    )

    soru = Soru(
        ders_id=data.ders_id,
        ogrenci_id=cu.id,
        soru_encrypted=encrypt_data(data.soru),
        ai_cevap_encrypted=encrypt_data(answer),
        anladi_mi=auto_anladi,
        ai_tahmin=True,
    )
    db.add(soru)
    db.commit()
    db.refresh(soru)

    check_notification_threshold(db, data.ders_id, lesson.hoca_id)

    return {"cevap": answer, "soru_id": soru.id}


@router.get("/teacher/breakdown/{ders_id}")
def lesson_breakdown(ders_id: int, db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)
    if cu.role != "teacher":
        raise HTTPException(status_code=403, detail=get_error("unauthorized", lang))

    lesson = db.query(Ders).filter(Ders.id == ders_id, Ders.hoca_id == cu.id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail=get_error("lesson_not_found", lang))

    ogrenciler = db.query(User).filter(User.hoca_id == cu.id, User.role == "student").all()

    result = []
    for ogr in ogrenciler:
        sorular = (
            db.query(Soru)
            .filter(Soru.ders_id == ders_id, Soru.ogrenci_id == ogr.id)
            .order_by(Soru.timestamp.asc())
            .all()
        )
        if not sorular:
            continue

        toplam = len([s for s in sorular if s.anladi_mi is not None])
        anlamadi = len([s for s in sorular if s.anladi_mi == False])
        anladi = len([s for s in sorular if s.anladi_mi == True])

        result.append({
            "ogrenci_id": ogr.id,
            "ad": decrypt_data(ogr.ad_encrypted),
            "soyad": decrypt_data(ogr.soyad_encrypted),
            "toplam_soru": len(sorular),
            "anladi": anladi,
            "anlamadi": anlamadi,
            "durum": "anlamadi" if anlamadi > 0 else ("anladi" if anladi > 0 else "sorsuz"),
            "sorular": [
                {
                    "id": s.id,
                    "soru": decrypt_data(s.soru_encrypted),
                    "anladi_mi": s.anladi_mi,
                    "ai_tahmin": s.ai_tahmin,
                    "timestamp": s.timestamp.isoformat(),
                }
                for s in sorular
            ],
        })

    result.sort(key=lambda x: (-x["anlamadi"], x["ad"]))
    return {
        "ders_id": ders_id,
        "tema": decrypt_data(lesson.tema_encrypted),
        "ogrenciler": result,
    }


@router.post("/teacher/ai")
async def teacher_ai(data: AiMessageRequest, db: Session = Depends(get_db), cu: User = Depends(get_current_user_fast)):
    lang = get_user_lang(cu)
    if cu.role != "teacher":
        raise HTTPException(status_code=403, detail=get_error("unauthorized", lang))

    lessons = db.query(Ders).filter(Ders.hoca_id == cu.id).all()

    teacher_prompts = TEACHER_AI_PROMPTS.get(lang, TEACHER_AI_PROMPTS["en"])

    ders_listesi = ", ".join(decrypt_data(l.tema_encrypted) for l in lessons) or teacher_prompts["no_lessons"]

    user_lang = cu.dil or "tr"
    lang_name = LANG_NAMES.get(user_lang, "English")

    ad = decrypt_data(cu.ad_encrypted) if getattr(cu, "ad_encrypted", None) else ""
    soyad = decrypt_data(cu.soyad_encrypted) if getattr(cu, "soyad_encrypted", None) else ""

    ogrenciler = db.query(User).filter(User.hoca_id == cu.id, User.role == "student").all()
    ogrenci_bilgi = []
    for o in ogrenciler:
        sorular = db.query(Soru).filter(Soru.ogrenci_id == o.id).all()
        anladi = sum(1 for s in sorular if s.anladi_mi == True)
        anlamadi = sum(1 for s in sorular if s.anladi_mi == False)
        ogrenci_bilgi.append({
            "ad": decrypt_data(o.ad_encrypted),
            "soyad": decrypt_data(o.soyad_encrypted),
            "toplam_soru": len(sorular),
            "anladi": anladi,
            "anlamadi": anlamadi
        })

    konu_istas = {}
    for l in lessons:
        sorular = db.query(Soru).filter(Soru.ders_id == l.id).all()
        if not sorular:
            continue
        anlamadi = sum(1 for s in sorular if s.anladi_mi == False)
        toplam = len([s for s in sorular if s.anladi_mi is not None])
        if toplam > 0:
            konu_istas[decrypt_data(l.tema_encrypted)] = {
                "anlamadi_yuzde": int(anlamadi / toplam * 100),
                "toplam_soru": toplam
            }

    zor_konular = sorted(konu_istas.items(), key=lambda x: x[1]["anlamadi_yuzde"], reverse=True)[:3]
    zor_konular_str = "\n".join([f"- {k}: %{v['anlamadi_yuzde']} anlamadı ({v['toplam_soru']} soru)" for k, v in zor_konular]) or teacher_prompts["no_data"]

    system = f"""{teacher_prompts['intro'].format(ad=ad, soyad=soyad)}
{teacher_prompts['task']}
{teacher_prompts['profile'].format(ad=ad, soyad=soyad, lang_name=lang_name, ogrenci_count=len(ogrenciler), ders_count=len(lessons))}
## Öğrenci Özeti
{json.dumps(ogrenci_bilgi[:5], ensure_ascii=False, indent=2) if ogrenci_bilgi else teacher_prompts['no_students']}
## Dersler
{ders_listesi}
## {teacher_prompts['difficult_topics']}
{zor_konular_str}
{teacher_prompts['rules'].format(lang_name=lang_name)}
{teacher_prompts['request']}
{data.message}"""

    answer = await call_openrouter(data.message, system, temperature=0.8, max_tokens=1500, user_lang=user_lang)
    return {"cevap": answer}