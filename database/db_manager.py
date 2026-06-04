# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import logging
from datetime import datetime
from config.settings import DB_FILE

def init_db():
    """全自动初始化 6 张核心关联表"""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # 1. 食材基础配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items_config (
                item_name TEXT PRIMARY KEY,
                loss_type TEXT,
                current_stock REAL DEFAULT 0.0,
                safety_stock REAL DEFAULT 20.0,
                unit TEXT DEFAULT 'kg'
            )
        """)
        # 2. 销售与外部环境历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_history (
                date TEXT,
                item_name TEXT,
                sales REAL DEFAULT 0.0,
                temperature REAL DEFAULT 25.0,
                waste_qty REAL DEFAULT 0.0,
                PRIMARY KEY (date, item_name)
            )
        """)
        # 3. 采购订单记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchase_orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                item_name TEXT,
                purchase_qty REAL,
                total_cost REAL,
                supplier TEXT
            )
        """)
        # 4. 库存流水审计明细表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_transactions (
                tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                item_name TEXT,
                tx_type TEXT, 
                qty_change REAL, 
                source_ref TEXT
            )
        """)
        # 5. 单品物料清单配比表（单品BOM）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dish_bom (
                dish_name TEXT,
                ingredient_name TEXT,
                required_qty_kg REAL,
                PRIMARY KEY (dish_name, ingredient_name)
            )
        """)
        # 6. 复合套餐组成配置表（套餐BOM）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS combo_config (
                combo_name TEXT,
                dish_name TEXT,
                dish_qty INTEGER,
                PRIMARY KEY (combo_name, dish_name)
            )
        """)
        # 7. AI 报告缓存表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_reports (
                date TEXT,
                item_name TEXT,
                report_content TEXT,
                PRIMARY KEY (date, item_name)
            )
        """)
        conn.commit()

def process_unified_ai_batch(items_list):
    """
    ⚡ 统一库存事务写入总线（支持批量列表处理）
    完美吸收来自 AI 网关识别出来的各种事务，内部自动判定、自动穿透拆单、秒级扣料。
    """
    timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    success_logs = []
    error_logs = []
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            for item in items_list:
                action_type = item['action_type']
                target_name = item['target_name'].strip()
                qty = item['qty']
                cost = item.get('total_cost', 0.0)
                supplier = item.get('supplier', "")
                
                # --- 模式一：采购入库 ---
                if action_type == "采购入库":
                    cursor.execute("INSERT OR IGNORE INTO items_config (item_name, loss_type) VALUES (?, '中损耗冷链肉类')", (target_name,))
                    cursor.execute("INSERT INTO purchase_orders (date, item_name, purchase_qty, total_cost, supplier) VALUES (?, ?, ?, ?, ?)", (date_str, target_name, qty, cost, supplier))
                    cursor.execute("INSERT INTO inventory_transactions (timestamp, item_name, tx_type, qty_change, source_ref) VALUES (?, ?, '采购入库', ?, ?)", (timestamp_str, target_name, qty, f"采购于: {supplier or '未知'}"))
                    cursor.execute("UPDATE items_config SET current_stock = current_stock + ? WHERE item_name = ?", (qty, target_name))
                    success_logs.append(f"📥 成功处理进货：【{target_name}】入库 {qty}kg")
                
                # --- 模式二：打烊报损 ---
                elif action_type == "打烊报损":
                    cursor.execute("INSERT OR IGNORE INTO items_config (item_name, loss_type) VALUES (?, '中损耗冷链肉类')", (target_name,))
                    cursor.execute("INSERT INTO inventory_transactions (timestamp, item_name, tx_type, qty_change, source_ref) VALUES (?, ?, '打烊报损', ?, '打烊模块报损')", (timestamp_str, target_name, -qty))
                    cursor.execute("UPDATE items_config SET current_stock = current_stock - ? WHERE item_name = ?", (qty, target_name))
                    cursor.execute("INSERT INTO sales_history (date, item_name, waste_qty) VALUES (?, ?, ?) ON CONFLICT(date, item_name) DO UPDATE SET waste_qty = waste_qty + ?", (date_str, target_name, qty, qty))
                    success_logs.append(f"🗑️ 成功处理报损：【{target_name}】扣减 {qty}kg")
                
                # --- 模式三：前台销售扣料（核心难点：动态跨多表穿透拆单） ---
                elif action_type == "销售扣料":
                    dishes_to_process = []
                    # 1. 动态探查该名称是否在套餐注册表(combo_config)中
                    cursor.execute("SELECT dish_name, dish_qty FROM combo_config WHERE combo_name = ?", (target_name,))
                    combo_rows = cursor.fetchall()
                    
                    if combo_rows:
                        # 是套餐，将套餐内的单品根据套数加权展开
                        for s_dish, s_qty in combo_rows:
                            dishes_to_process.append((s_dish, qty * s_qty))
                        source_tag = f"AI网关销售套餐: {target_name}"
                    else:
                        # 不是套餐，当成独立菜品处理
                        dishes_to_process.append((target_name, qty))
                        source_tag = f"AI网关单品独立下单"
                    
                    # 2. 依次解析各单品在单品配方表(dish_bom)对应的原材料配方进行精准扣料
                    sub_deduct_details = []
                    for item_dish, final_count in dishes_to_process:
                        cursor.execute("SELECT ingredient_name, required_qty_kg FROM dish_bom WHERE dish_name = ?", (item_dish,))
                        ingredients = cursor.fetchall()
                        
                        if not ingredients:
                            error_logs.append(f"❌ 无法处理【{target_name}】扣料：未配置菜品【{item_dish}】的食材BOM配方，请在模块6中添加。")
                            continue
                            
                        for ing_name, req_qty in ingredients:
                            total_deduct = round(req_qty * final_count, 2)
                            
                            # 扣减主库存
                            cursor.execute("UPDATE items_config SET current_stock = current_stock - ? WHERE item_name = ?", (total_deduct, ing_name))
                            # 记入明细审计流水
                            cursor.execute("INSERT INTO inventory_transactions (timestamp, item_name, tx_type, qty_change, source_ref) VALUES (?, ?, '销售扣料', ?, ?)", (timestamp_str, ing_name, -total_deduct, f"{source_tag} (拆解至 {item_dish} * {final_count})"))
                            # 累加历史时序销量
                            cursor.execute("INSERT INTO sales_history (date, item_name, sales) VALUES (?, ?, ?) ON CONFLICT(date, item_name) DO UPDATE SET sales = sales + ?", (date_str, ing_name, total_deduct, total_deduct))
                            
                            sub_deduct_details.append(f"{ing_name} -{total_deduct}kg")
                    
                    if sub_deduct_details:
                        success_logs.append(f"🛒 成功处理前台收银：【{target_name}】*{qty}份，穿透扣料明细：({', '.join(sub_deduct_details)})")
            
            conn.commit()
            return True, success_logs, error_logs
    except Exception as e:
        logging.exception("执行统一 AI 批量库存处理时崩溃")
        return False, [], [f"底层系统崩溃: {str(e)}"]

# --- 以下为常规 CRUD 与展示提取函数 ---
def get_stock_metrics():
    with sqlite3.connect(DB_FILE) as conn:
        return pd.read_sql_query("SELECT item_name, loss_type, current_stock, safety_stock, unit FROM items_config", conn)

def get_all_items():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT item_name FROM items_config")
            return [row[0] for row in cursor.fetchall()]
    except Exception: return []

def load_data_from_db(item_name):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            query = "SELECT date, sales, temperature, waste_qty FROM sales_history WHERE item_name = ? ORDER BY date ASC"
            df = pd.read_sql_query(query, conn, params=(item_name,))
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            return df
    except Exception: return pd.DataFrame()

def add_new_item_to_db(item_name, loss_type, safety_stock=20.0, init_stock=50.0):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.cursor().execute("INSERT OR REPLACE INTO items_config (item_name, loss_type, safety_stock, current_stock, unit) VALUES (?, ?, ?, ?, 'kg')", (item_name, loss_type, safety_stock, init_stock))
            conn.commit()
        return True
    except Exception: return False

def delete_item_from_db(item_name):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.cursor().execute("DELETE FROM items_config WHERE item_name = ?", (item_name,))
            conn.commit()
        return True
    except Exception: return False

def add_new_combo_to_db(combo_name, dish_name, dish_qty):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.cursor().execute("INSERT OR REPLACE INTO combo_config (combo_name, dish_name, dish_qty) VALUES (?, ?, ?)", (combo_name, dish_name, dish_qty))
            conn.commit()
        return True
    except Exception: return False

def get_all_combos_from_db():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT combo_name FROM combo_config")
            return [row[0] for row in cursor.fetchall()]
    except Exception: return []

def get_combo_details_df():
    with sqlite3.connect(DB_FILE) as conn:
        return pd.read_sql_query("SELECT combo_name AS '套餐名称', dish_name AS '包含单品', dish_qty AS '组成份数' FROM combo_config", conn)

def add_new_dish_bom_to_db(dish_name, ingredient_name, required_qty_kg):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.cursor().execute("INSERT OR REPLACE INTO dish_bom (dish_name, ingredient_name, required_qty_kg) VALUES (?, ?, ?)", (dish_name, ingredient_name, required_qty_kg))
            conn.commit()
        return True
    except Exception: return False

def get_dish_bom_details_df():
    with sqlite3.connect(DB_FILE) as conn:
        return pd.read_sql_query("SELECT dish_name AS '单品名称', ingredient_name AS '消耗食材', required_qty_kg AS '单份用量(kg)' FROM dish_bom", conn)

def check_and_seed_db():
    init_db()
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        initial_items = [
            ('鸡肉', '中损耗冷链肉类', 50.0, 20.0, 'kg'),
            ('牛肉', '中损耗冷链肉类', 45.0, 15.0, 'kg'),
            ('花生', '低损耗仓储主食', 30.0, 10.0, 'kg')
        ]
        for name, loss, cur, saf, unit in initial_items:
            cursor.execute("INSERT OR IGNORE INTO items_config (item_name, loss_type, current_stock, safety_stock, unit) VALUES (?, ?, ?, ?, ?)", (name, loss, cur, saf, unit))
            
        initial_boms = [
            ('宫保鸡丁', '鸡肉', 0.20),
            ('宫保鸡丁', '花生', 0.05),
            ('黑椒牛柳', '牛肉', 0.25)
        ]
        for dish, ing, req in initial_boms:
            cursor.execute("INSERT OR IGNORE INTO dish_bom (dish_name, ingredient_name, required_qty_kg) VALUES (?, ?, ?)", (dish, ing, req))
            
        cursor.execute("SELECT COUNT(*) FROM combo_config")
        if cursor.fetchone()[0] == 0:
            default_combos = [
                ("超值双人套餐", "宫保鸡丁", 1), ("超值双人套餐", "黑椒牛柳", 1),
                ("全肉狂欢套餐", "黑椒牛柳", 2), ("单人商务套餐", "宫保鸡丁", 1)
            ]
            for c_name, d_name, d_qty in default_combos:
                cursor.execute("INSERT INTO combo_config (combo_name, dish_name, dish_qty) VALUES (?, ?, ?)", (c_name, d_name, d_qty))

        cursor.execute("SELECT COUNT(*) FROM sales_history")
        if cursor.fetchone()[0] == 0:
            import random
            from datetime import datetime, timedelta
            base_date = datetime.now() - timedelta(days=20)
            for i in range(21):
                current_date_str = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
                sim_temp = round(random.uniform(26.0, 33.0), 1)
                sim_sales_chicken = round(random.uniform(25.0, 40.0), 2)
                cursor.execute("INSERT INTO sales_history (date, item_name, sales, temperature, waste_qty) VALUES (?, '鸡肉', ?, ?, 0.0)", (current_date_str, sim_sales_chicken, sim_temp))
                sim_sales_beef = round(random.uniform(20.0, 35.0), 2)
                cursor.execute("INSERT INTO sales_history (date, item_name, sales, temperature, waste_qty) VALUES (?, '牛肉', ?, ?, 0.0)", (current_date_str, sim_sales_beef, sim_temp))
        conn.commit()