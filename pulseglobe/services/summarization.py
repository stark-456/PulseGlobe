"""
摘要生成服务
为采集的数据生成100字以内的摘要
"""
import logging

from langchain_core.messages import HumanMessage

from pulseglobe.services.llm import get_llm_client

logger = logging.getLogger(__name__)


SUMMARIZATION_PROMPT = """请为以下内容生成一个简短摘要，要求：
1. **100字以内**
2. 突出核心信息
3. 保留关键事实（人物、事件、时间、地点）
4. 使用中文

## 原文
{content}

## 输出
只输出摘要内容，不要有任何前缀或解释。"""


class SummarizationService:
    """摘要生成服务"""
    
    def __init__(self):
        self.llm = get_llm_client()
    
    async def summarize(self, content: str, title: str = "") -> str:
        """
        生成摘要
        
        Args:
            content: 正文内容
            title: 可选的标题
            
        Returns:
            100字以内的摘要
        """
        if not content or not content.strip():
            return ""
        
        # 拼接标题和内容
        full_text = content
        if title:
            full_text = f"标题：{title}\n\n{content}"
        
        # 如果内容太短，直接返回
        if len(full_text) < 100:
            return full_text
        
        # 截断过长内容（避免超长输入）
        if len(full_text) > 3000:
            full_text = full_text[:3000] + "..."
        
        prompt = SUMMARIZATION_PROMPT.format(content=full_text)
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            summary = response.content.strip()
            
            # 确保不超过100字
            if len(summary) > 100:
                summary = summary[:97] + "..."
            
            return summary
        except Exception as e:
            logger.error(f"摘要生成失败: {e}")
            # 失败时返回截断的原文
            return content[:100] if len(content) > 100 else content
