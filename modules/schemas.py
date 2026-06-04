# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from typing import List, Optional

class LedgerItem(BaseModel):
    action_type: str = Field(description="事务类型，必须是以下三者之一: '采购入库', '打烊报损', '销售扣料'")
    target_name: str = Field(description="操作的目标名称。如果 action_type 是 '采购入库' 或 '打烊报损'，这里填写底层原始食材名（如：鸡肉、牛肉、小龙虾）；如果 action_type 是 '销售扣料'，这里填写售出的前台菜品或套餐名（如：宫保鸡丁、黑椒牛柳、超值双人套餐）")
    qty: float = Field(description="操作的业务物理数量（如采购公斤数、报损公斤数、或菜品售出的份数/套数）")
    total_cost: Optional[float] = Field(default=0.0, description="采购总成本金额，仅在 action_type 为 '采购入库' 时可能存在，其余情况为 0.0")
    supplier: Optional[str] = Field(default="", description="供应商名称，仅在采购时可能存在，其余情况为空字符串")

class UnifiedLedgerResponse(BaseModel):
    items: List[LedgerItem] = Field(description="解析出来的账目或销售流水列表，支持单条或多条同时输入")