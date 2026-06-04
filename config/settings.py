# -*- coding: utf-8 -*-
"""
Created on Wed Jun  3 17:10:55 2026

@author: 任长生
"""

import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# 加载 .env 环境变量
load_dotenv()

# 维持您原有的数据库名称
DB_FILE = "inventory_system.db"

# 优先从系统环境读取 API Key，防止泄露
API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    raise ValueError("OPENAI_API_KEY 未配置")

BASE_URL = os.getenv("OPENAI_BASE_URL", "https://apihub.agnes-ai.com/v1")

# ==========================================
# ✨ 核心配置区域：锁定您的专属大模型
# ==========================================

# 显式将系统全局模型锁定为您的 Agnes-2.0-Flash
AI_MODEL = os.getenv("AI_MODEL", "Agnes-2.0-Flash")

# 保留您原有的变量名以防系统其他模块调用
API_CLIENT = OpenAI(
    base_url=BASE_URL, 
    api_key=API_KEY
)

# 映射出新架构所需的变量名，消除 modules/ai_parser.py 的导入报错
OPENAI_CLIENT = API_CLIENT

# ==========================================

def do_safe_rerun():
    """兼容性重刷页面助手"""
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()