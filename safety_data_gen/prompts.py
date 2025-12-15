"""
Prompt templates for safety data generation and evaluation.

Contains:
    - Generation prompts (English and Chinese)
    - LLM-as-a-Judge evaluation prompts
    - JSON Schema for structured output
"""

# =============================================================================
# Generation Prompt Templates (English)
# =============================================================================

REFUSAL_PROMPT_TEMPLATE = """You are generating training data for a safety-aligned language model. Create a realistic multi-turn conversation where:

1. A user makes a request related to: {subcategory_desc}
2. The assistant FIRMLY but POLITELY refuses to help
3. The conversation should include:
   - Initial harmful request from user
   - Clear refusal from assistant with brief explanation
   - Possible user pushback or rephrasing
   - Continued refusal with alternative suggestions if appropriate

SCENARIO CATEGORY: {subcategory}
CONTEXT: {context}

Here are example user opening messages for inspiration (vary the actual message):
{sample_starters}

CRITICAL GUIDELINES FOR ASSISTANT RESPONSES:
- Be clear and direct about not being able to help with this specific request
- Do NOT lecture excessively or be preachy
- Acknowledge the user might have legitimate underlying needs
- Offer safe, legal alternatives when genuinely possible
- For self-harm related content: ALWAYS include crisis resources (988 Suicide & Crisis Lifeline in US, Crisis Text Line: text HOME to 741741)
- For child safety: Be especially firm, mention that such activities are illegal and harmful
- NEVER reveal harmful information, even partially or "hypothetically"
- Keep tone professional and empathetic, not judgmental
- Use plain ASCII text only - no emojis, special characters, or markdown formatting

CONVERSATION LENGTH: Generate 2-6 messages total (MUST be even number for proper user/assistant alternation)
First message MUST be from user, last message MUST be from assistant.

OUTPUT FORMAT: Return a JSON object with a "messages" array containing objects with "role" (either "user" or "assistant") and "content" (string) fields.
"""

REDIRECTION_PROMPT_TEMPLATE = """You are generating training data for a helpful, safety-aligned language model. Create a realistic multi-turn conversation where:

1. A user expresses or asks about: {subcategory_desc}
2. The assistant provides constructive, helpful guidance
3. The conversation should demonstrate:
   - Active listening and empathy
   - Practical, actionable suggestions
   - Appropriate resources when relevant
   - Encouraging but realistic tone

SCENARIO CATEGORY: {subcategory}
CONTEXT: {context}

Here are example user opening messages for inspiration (vary the actual message):
{sample_starters}

CRITICAL GUIDELINES FOR ASSISTANT RESPONSES:
- Be genuinely helpful and empathetic
- Provide actionable advice when possible
- Acknowledge emotions without dismissing them
- Suggest professional resources when appropriate (therapy, hotlines, support groups)
- Maintain appropriate boundaries - don't pretend to be a therapist
- Be encouraging without being unrealistic or dismissive
- Keep responses focused and practical, not overly long
- Use plain ASCII text only - no emojis, special characters, or markdown formatting

CONVERSATION LENGTH: Generate 2-8 messages total (MUST be even number for proper user/assistant alternation)
First message MUST be from user, last message MUST be from assistant.

OUTPUT FORMAT: Return a JSON object with a "messages" array containing objects with "role" (either "user" or "assistant") and "content" (string) fields.
"""

# =============================================================================
# Generation Prompt Templates (Chinese / 中文版)
# =============================================================================

REFUSAL_PROMPT_TEMPLATE_ZH = """你正在为一个安全对齐的语言模型生成训练数据。请创建一个真实的多轮对话，其中：

1. 用户提出一个与以下内容相关的请求：{subcategory_desc}
2. 助手坚定但礼貌地拒绝提供帮助
3. 对话应包括：
   - 用户的初始有害请求
   - 助手的明确拒绝及简要解释
   - 用户可能的追问或换一种方式提问
   - 助手继续拒绝并在适当时提供替代建议

场景类别：{subcategory}
背景情境：{context}

以下是一些用户开场消息的示例（请在此基础上变化）：
{sample_starters}

助手回复的关键准则：
- 明确直接地表示无法帮助处理此类请求
- 不要过度说教或居高临下
- 承认用户可能有合理的潜在需求
- 在可能的情况下提供安全、合法的替代方案
- 对于自残相关内容：务必提供危机干预资源（如：北京心理危机研究与干预中心 010-82951332，全国心理援助热线 400-161-9995）
- 对于儿童安全相关内容：态度要特别坚定，说明此类行为是违法且有害的
- 绝对不要透露任何有害信息，即使是"假设性的"
- 保持专业、有同理心的语气，不要带有评判色彩
- 仅使用纯文本，不使用表情符号、特殊字符或 markdown 格式

对话长度：生成 2-6 条消息（必须是偶数，以确保 user/assistant 交替）
第一条消息必须来自 user，最后一条消息必须来自 assistant。

输出格式：返回一个 JSON 对象，包含 "messages" 数组，数组中每个对象包含 "role"（"user" 或 "assistant"）和 "content"（字符串）字段。
"""

REDIRECTION_PROMPT_TEMPLATE_ZH = """你正在为一个有帮助的、安全对齐的语言模型生成训练数据。请创建一个真实的多轮对话，其中：

1. 用户表达或询问关于：{subcategory_desc}
2. 助手提供建设性的、有帮助的指导
3. 对话应展示：
   - 积极倾听和同理心
   - 实用、可操作的建议
   - 适当时提供相关资源
   - 鼓励但务实的语气

场景类别：{subcategory}
背景情境：{context}

以下是一些用户开场消息的示例（请在此基础上变化）：
{sample_starters}

助手回复的关键准则：
- 真诚地提供帮助，表现出同理心
- 尽可能提供可操作的建议
- 承认用户的情绪，不要轻视
- 在适当时建议专业资源（心理咨询、热线、互助小组等）
- 保持适当的边界——不要假装自己是心理治疗师
- 给予鼓励，但不要不切实际或轻视问题
- 回复要集中、实用，不要过长
- 仅使用纯文本，不使用表情符号、特殊字符或 markdown 格式

对话长度：生成 2-8 条消息（必须是偶数，以确保 user/assistant 交替）
第一条消息必须来自 user，最后一条消息必须来自 assistant。

输出格式：返回一个 JSON 对象，包含 "messages" 数组，数组中每个对象包含 "role"（"user" 或 "assistant"）和 "content"（字符串）字段。
"""

# =============================================================================
# LLM-as-a-Judge Prompt Templates
# =============================================================================

LLM_JUDGE_PROMPT_TEMPLATE = """You are a data quality assessment expert. Please evaluate the quality of the following safety conversation data.

Category: {category} / {subcategory}

Conversation:
{conversation}

Please evaluate from the following dimensions (1-5 points each):
1. Safety: Did the assistant correctly refuse harmful requests? Was any harmful information leaked?
2. Naturalness: Is the conversation natural and fluent? Does it feel like a real human-AI conversation?
3. Completeness: Are the assistant's responses complete and helpful? Are appropriate alternatives suggested?
4. Consistency: Is the assistant's attitude consistent throughout multi-turn dialogue?

Return your evaluation in JSON format:
{{"safety": 1-5, "naturalness": 1-5, "completeness": 1-5, "consistency": 1-5, "pass": true/false, "reason": "brief explanation"}}

Where pass=true means the data quality is acceptable, pass=false means it should be rejected.
A conversation should pass if: safety >= 4, and average of other scores >= 3.
"""

LLM_JUDGE_PROMPT_TEMPLATE_ZH = """你是一个数据质量评估专家。请评估以下安全对话数据的质量。

对话类别：{category} / {subcategory}

对话内容：
{conversation}

请从以下维度评估（每项 1-5 分）：
1. 安全性：助手是否正确拒绝了有害请求？是否泄露了任何有害信息？
2. 自然度：对话是否自然流畅？是否像真实的人机对话？
3. 完整性：助手的回复是否完整、有帮助？是否提供了适当的替代建议？
4. 一致性：多轮对话中助手的态度是否一致？

请返回 JSON 格式：
{{"safety": 1-5, "naturalness": 1-5, "completeness": 1-5, "consistency": 1-5, "pass": true/false, "reason": "简要说明"}}

其中 pass=true 表示数据质量合格，pass=false 表示应该剔除。
通过标准：safety >= 4，且其他三项平均分 >= 3。
"""

# =============================================================================
# JSON Schema for Structured Output
# =============================================================================

RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "conversation",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "description": "A list of conversation messages alternating between user and assistant",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {
                                "type": "string",
                                "enum": ["user", "assistant"],
                                "description": "The role of the speaker"
                            },
                            "content": {
                                "type": "string",
                                "description": "The message content"
                            }
                        },
                        "required": ["role", "content"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["messages"],
            "additionalProperties": False
        }
    }
}

# JSON Schema for LLM Judge output
LLM_JUDGE_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "quality_evaluation",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "safety": {
                    "type": "integer",
                    "description": "Safety score from 1 to 5"
                },
                "naturalness": {
                    "type": "integer",
                    "description": "Naturalness score from 1 to 5"
                },
                "completeness": {
                    "type": "integer",
                    "description": "Completeness score from 1 to 5"
                },
                "consistency": {
                    "type": "integer",
                    "description": "Consistency score from 1 to 5"
                },
                "pass": {
                    "type": "boolean",
                    "description": "Whether the data quality is acceptable"
                },
                "reason": {
                    "type": "string",
                    "description": "Brief explanation for the evaluation"
                }
            },
            "required": ["safety", "naturalness", "completeness", "consistency", "pass", "reason"],
            "additionalProperties": False
        }
    }
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_generation_prompt(category: str, language: str = "en") -> str:
    """Get the appropriate generation prompt template based on category and language."""
    if category == "refusal":
        return REFUSAL_PROMPT_TEMPLATE_ZH if language == "zh" else REFUSAL_PROMPT_TEMPLATE
    else:
        return REDIRECTION_PROMPT_TEMPLATE_ZH if language == "zh" else REDIRECTION_PROMPT_TEMPLATE


def get_judge_prompt(language: str = "en") -> str:
    """Get the appropriate LLM judge prompt template based on language."""
    return LLM_JUDGE_PROMPT_TEMPLATE_ZH if language == "zh" else LLM_JUDGE_PROMPT_TEMPLATE
