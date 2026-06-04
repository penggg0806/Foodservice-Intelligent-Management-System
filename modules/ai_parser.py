# -*- coding: utf-8 -*-
import json
import logging
from config.settings import OPENAI_CLIENT, AI_MODEL
from modules.schemas import UnifiedLedgerResponse

def analyze_unified_ledger_via_ai(text_input=None, image_file=None):
    """
    统一 AI 智能网关：
    接受文本输入或图片单据，全自动输出标准化的结构化事务列表（支持批量操作）。
    """
    prompt = """
    你现在是餐饮门店的智慧供应链 AI 数据清洗与审计专家。
    请将用户输入的口语化文本、收银下单指令或单据表格截图，深度清洗并归纳为统一的库存变动事务列表。
    
    【分类与行为规范（非常严厉，请严格遵守）】：
    1. 如果判断是进货、采购行为：
       - `action_type` 必须归类为 "采购入库"
       - `target_name` 必须提取为底层原始食材名（如：鸡肉、牛肉、小龙虾）
       - `qty` 为采购的公斤数
    2. 如果判断是店长打烊倒掉、损耗行为：
       - `action_type` 必须归类为 "打烊报损"
       - `target_name` 必须提取为底层原始食材名
       - `qty` 为报损废弃的公斤数
    3. 如果判断是门店前台点餐、收银、卖出菜品/套餐行为：
       - `action_type` 必须归类为 "销售扣料"
       - `target_name` 必须提取为售出的前台菜品名称或复合套餐名称（如：宫保鸡丁、黑椒牛柳、超值双人套餐、单人商务套餐）
       - `qty` 为售出的份数或套数
       
    【输出格式要求】：
    你必须严格输出符合以下 JSON Schema 的数据，不要附带任何 Markdown 标记或多余大白话解释：
    {
      "items": [
         {"action_type": "采购入库", "target_name": "牛肉", "qty": 30.0, "total_cost": 900.0, "supplier": "张老板"},
         {"action_type": "销售扣料", "target_name": "宫保鸡丁", "qty": 2.0, "total_cost": 0.0, "supplier": ""},
         {"action_type": "销售扣料", "target_name": "超值双人套餐", "qty": 1.0, "total_cost": 0.0, "supplier": ""}
      ]
    }
    """
    
    messages = [{"role": "system", "content": prompt}]
    
    if image_file:
        import base64
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        mime_type = image_file.type if hasattr(image_file, "type") else "image/jpeg"
        user_content = [
            {"type": "text", "text": "请仔细辨认并透视这张票据、初始库存表截图或盘点单，将其转换为事务列表："},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
        ]
        if text_input:
            user_content.append({"type": "text", "text": f"补充上下文备注：{text_input}"})
        messages.append({"role": "user", "content": user_content})
    else:
        if not text_input:
            return None
        messages.append({"role": "user", "content": f"请解析以下流水指令：'{text_input}'"})

    try:
        response = OPENAI_CLIENT.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0
        )
        raw_content = response.choices[0].message.content
        logging.info(f"AI 网关统一返回原始数据: {raw_content}")
        
        # 稳健解析与 Pydantic 强校验
        parsed_data = json.loads(raw_content)
        validated_res = UnifiedLedgerResponse(**parsed_data)
        return validated_res.dict()
    except Exception as e:
        logging.exception("AI 统一网关进行账目或销售清洗时发生崩溃")
        return None