# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from config.settings import do_safe_rerun
from database.db_manager import (
    check_and_seed_db, get_all_items, load_data_from_db, get_stock_metrics, 
    add_new_item_to_db, delete_item_from_db, add_new_combo_to_db, 
    get_all_combos_from_db, get_combo_details_df, add_new_dish_bom_to_db, 
    get_dish_bom_details_df, process_unified_ai_batch
)
from modules.ai_parser import analyze_unified_ledger_via_ai
from modules.models import run_statistical_model, load_or_generate_ai_report

st.set_page_config(page_title="餐饮门店智慧供应链与库存智能决策系统", page_icon="🥗", layout="wide")
check_and_seed_db()

st.markdown("""
    <style>
        .main-title { font-size: 2.2rem; font-weight: 800; color: #1B5E20; margin-bottom: 0.1rem; }
        .sub-title { font-size: 0.95rem; color: #555555; margin-bottom: 1.2rem; }
        .section-card { background-color: #FFFFFF; padding: 18px; border-radius: 8px; box-shadow: 0 3px 6px rgba(0,0,0,0.04); margin-top: 1.5rem; margin-bottom: 1.5rem; border: 1px solid #E0E0E0; }
        .section-header { font-size: 1.3rem; font-weight: 700; color: #2E7D32; border-bottom: 2px solid #C8E6C9; padding-bottom: 4px; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🥗 餐饮门店智慧供应链与库存智能决策系统</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">🤖 AI 统一网关版：不管是收银点单、店长记账、还是 Excel 初始库存表截图，全部由 AI 统一解析并安全落库</div>', unsafe_allow_html=True)

# 全局聚焦
st.sidebar.header("🎛️ 系统全局聚焦核心")
available_items = get_all_items()
selected_item = st.sidebar.selectbox("当前查看目标食材：", available_items if available_items else ["无可用食材"])

if selected_item and selected_item != "无可用食材":
    pure_item_name = selected_item.split(" ")[0].strip()
    history_df = load_data_from_db(pure_item_name)
    forecast_df, temp_coef, temp_pvalue = run_statistical_model(history_df)
else:
    history_df, forecast_df = pd.DataFrame(), pd.DataFrame()

# -------------------------------------------------------------
# 模块 1：AI 智能流转中枢网关
# -------------------------------------------------------------
st.markdown('<div class="section-card"><div class="section-header">1. AI 智能流转中枢网关（统一数据清洗与落库入口）</div>', unsafe_allow_html=True)
col_l1, col_l2 = st.columns([1, 1])

with col_l1:
    st.markdown("**✍️ 全能文本输入窗口（支持点单、记账、报损、盘点）**")
    text_ledger = st.text_area("在此输入任何指令，例如：\n- '前台卖出了2份宫保鸡丁，1份黑椒牛柳'\n- '刚到了50kg小龙虾，花销2000元，供应商是张老板'\n- '倒掉了3公斤过期的牛肉'", height=110)
    if st.button("🔥 提交指令至 AI 网关智能处理"):
        if text_ledger.strip():
            with st.spinner("AI 正在深度透视、归纳并执行批量拆单解耦..."):
                parsed_res = analyze_unified_ledger_via_ai(text_input=text_ledger.strip())
                if parsed_res and parsed_res.get('items'):
                    success, s_logs, e_logs = process_unified_ai_batch(parsed_res['items'])
                    for log in s_logs: st.success(log)
                    for log in e_logs: st.error(log)
                    if success: st.cache_data.clear(); do_safe_rerun()
                else: st.error("AI 未能识别有效库存变动。")

with col_l2:
    st.markdown("**📸 多模态视觉网关（支持进货单、初始库存 Excel 截图、纸质账本拍照）**")
    uploaded_img = st.file_uploader("上传单据、表格或收据截图：", type=["png", "jpg", "jpeg"])
    if st.button("👁️ AI 视觉批量解析并初始化库存"):
        if uploaded_img is not None:
            with st.spinner("大模型正在进行高精度全表穿透分析..."):
                parsed_res = analyze_unified_ledger_via_ai(image_file=uploaded_img)
                if parsed_res and parsed_res.get('items'):
                    success, s_logs, e_logs = process_unified_ai_batch(parsed_res['items'])
                    for log in s_logs: st.success(log)
                    for log in e_logs: st.error(log)
                    if success: st.cache_data.clear(); do_safe_rerun()
                else: st.error("视觉解析未提取到有效数据，请确保单据字迹清晰。")
st.markdown('</div>', unsafe_allow_html=True)


# -------------------------------------------------------------
# 模块 2：门店收银快速点单模拟器
# -------------------------------------------------------------
st.markdown('<div class="section-card"><div class="section-header">2. 前台快捷收银模拟器（一键合成口令并移交 AI 处理）</div>', unsafe_allow_html=True)
col_b1, col_b2 = st.columns([1, 1])

with col_b1:
    registered_combos = get_all_combos_from_db()
    with st.form("cashier_fast_form"):
        st.markdown("**🛒 快捷选择售出品类**")
        selected_target = st.selectbox("选择要结账的菜品或套餐：", (registered_combos + ["宫保鸡丁", "黑椒牛柳"]))
        sales_count = st.number_input("售出数量/份数：", min_value=1, value=1)
        
        if st.form_submit_button("⚡ 确认收银结账（交给 AI 自动扣料）"):
            # 统一打包成一段自然语言口令投喂给 AI 网关处理，实现端口统一！
            simulated_text = f"前台刚刚售出了 {sales_count} 份 {selected_target}，请立刻进行系统扣料。"
            with st.spinner("收银数据正穿过 AI 智能网关..."):
                parsed_res = analyze_unified_ledger_via_ai(text_input=simulated_text)
                if parsed_res and parsed_res.get('items'):
                    success, s_logs, e_logs = process_unified_ai_batch(parsed_res['items'])
                    if success: st.cache_data.clear(); do_safe_rerun()
                    else: st.error("收银失败：" + "; ".join(e_logs))

with col_b2:
    v_tab1, v_tab2 = st.tabs(["🍱 注册套餐资产", "🍳 单品基础配方(BOM)"])
    with v_tab1: st.dataframe(get_combo_details_df(), use_container_width=True, hide_index=True)
    with v_tab2: st.dataframe(get_dish_bom_details_df(), use_container_width=True, hide_index=True)
st.markdown('</div>', unsafe_allow_html=True)


# 模块 3：实时仓储与时序看板
st.markdown('<div class="section-card"><div class="section-header">3. 实时仓储状态审计与断货预警面板</div>', unsafe_allow_html=True)
metrics_df = get_stock_metrics()
if not metrics_df.empty:
    cols_m = st.columns(min(len(metrics_df), 4))
    for idx, row in metrics_df.iterrows():
        col_target = cols_m[idx % 4]
        is_danger = row['current_stock'] < row['safety_stock']
        col_target.metric(label=f"⚠️ {row['item_name']}" if is_danger else f"🍏 {row['item_name']}", value=f"{row['current_stock']:.2f} {row['unit']}", delta=f"安全阈值: {row['safety_stock']}")
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)
st.markdown('</div>', unsafe_allow_html=True)


# 模块 4 & 5：销量趋势与智能指南
st.markdown('<div class="section-card"><div class="section-header">4. 时序模型预测与 AI 自动化备货指南</div>', unsafe_allow_html=True)
if not history_df.empty and not forecast_df.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=history_df.index, y=history_df['sales'], name='历史消耗', mode='lines+markers', line=dict(color='#2E7D32')))
    fig.add_trace(go.Scatter(x=forecast_df.index, y=forecast_df['forecast_sales'], name='预测趋势', mode='lines+markers', line=dict(color='#EF6C00', dash='dash')))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(load_or_generate_ai_report(forecast_df, temp_coef, temp_pvalue, selected_item.split(" ")[0].strip()))
st.markdown('</div>', unsafe_allow_html=True)


# 模块 6：品类与配方配置大本营 (CRUD)
st.markdown('<div class="section-card"><div class="section-header">5. 商户资产与全链路配方配置大本营</div>', unsafe_allow_html=True)
col_c1, col_c2 = st.columns(2)
with col_c1:
    st.markdown("**➕ 建立新原材料食材档案**")
    with st.form("add_item_form"):
        new_name = st.text_input("食材品类名：")
        new_loss = st.selectbox("损耗特征：", ["中损耗冷链肉类", "低损耗仓储主食", "高损耗鲜活蔬菜"])
        if st.form_submit_button("确认建立食材"):
            if new_name.strip() and add_new_item_to_db(new_name.strip(), new_loss): st.cache_data.clear(); do_safe_rerun()
with col_c2:
    st.markdown("**❌ 注销现有食材品类**")
    with st.form("delete_item_form"):
        item_to_del = st.selectbox("选择淘汰食材：", available_items if available_items else ["无"])
        if st.form_submit_button("确认从系统注销", type="primary"):
            if item_to_del and item_to_del != "无":
                if delete_item_from_db(item_to_del.split(" ")[0].strip()): st.cache_data.clear(); do_safe_rerun()

st.markdown("---")
col_f_combo, col_f_dish = st.columns(2)
with col_f_combo:
    st.markdown("**🍱 配置 套餐 ➔ 包含哪些单品菜品**")
    with st.form("add_combo_form"):
        c_name = st.text_input("套餐名称", value="新春合家欢套餐")
        d_name = st.text_input("包含单品菜名")
        d_qty = st.number_input("份数", min_value=1, value=1)
        if st.form_submit_button("绑定套餐关系"):
            if c_name.strip() and d_name.strip() and add_new_combo_to_db(c_name.strip(), d_name.strip(), d_qty): st.cache_data.clear(); do_safe_rerun()

with col_f_dish:
    st.markdown("**🍳 配置 单品菜品 ➔ 消耗底层的哪些原始食材(BOM)**")
    with st.form("add_bom_form"):
        dish_target = st.text_input("单品名称", value="宫保鸡丁")
        ing_target = st.selectbox("消耗的食材：", available_items if available_items else ["请先新建食材档案"])
        ing_qty = st.number_input("单份用量 (kg)：", min_value=0.01, value=0.20, step=0.01)
        if st.form_submit_button("发布单品基础BOM"):
            if dish_target.strip() and ing_target != "请先新建食材档案":
                if add_new_dish_bom_to_db(dish_target.strip(), ing_target.split(" ")[0].strip(), ing_qty): st.cache_data.clear(); do_safe_rerun()
st.markdown('</div>', unsafe_allow_html=True)