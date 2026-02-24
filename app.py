"""
💎 Finance AI — Smart Financial Document Analyzer
AI-powered analysis of invoices, statements, receipts, and CSV files
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
from datetime import date
from sqlalchemy import text
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_engine, init_db
from ai_parser import parse_document, parse_text_document, parse_csv_file, CATEGORY_ICONS, CATEGORY_COLORS

# ── Config ─────────────────────────────────────────────────────
st.set_page_config(page_title="Finance AI", page_icon="💎", layout="wide", initial_sidebar_state="expanded")

# ── CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;700;900&display=swap');
* { font-family: 'Inter', sans-serif !important; }
.stApp { background: #080c14; color: #e2e8f0; }
section[data-testid="stSidebar"] { background: #0d1117 !important; border-right: 1px solid rgba(99,102,241,0.2); }
.hero {
    background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 50%, #0c1a3a 100%);
    border: 1px solid rgba(99,102,241,0.3); border-radius: 20px;
    padding: 36px 40px; margin-bottom: 28px;
}
.hero h1 {
    font-size: 2.2rem !important; font-weight: 900 !important;
    background: linear-gradient(135deg, #818cf8, #34d399);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0 0 8px 0 !important;
}
.hero p { color: rgba(255,255,255,0.55); font-size: 1rem; margin: 0; }
.kpi-card {
    background: linear-gradient(135deg, #0d1117, #161b27);
    border: 1px solid rgba(99,102,241,0.2); border-radius: 16px;
    padding: 22px 24px; margin-bottom: 16px; position: relative; overflow: hidden;
}
.kpi-card::after {
    content: ''; position: absolute; bottom: 0; left: 0; right: 0;
    height: 2px; background: linear-gradient(90deg, #6366f1, #34d399);
}
.kpi-value { font-size: 2rem; font-weight: 900; color: #818cf8; line-height: 1; }
.kpi-value.income { color: #34d399; }
.kpi-value.expense { color: #f87171; }
.kpi-label { font-size: 0.8rem; color: rgba(255,255,255,0.4); margin-top: 8px; }
.insight-card {
    background: linear-gradient(135deg, rgba(99,102,241,0.12), rgba(52,211,153,0.08));
    border: 1px solid rgba(99,102,241,0.25); border-radius: 12px;
    padding: 14px 18px; margin: 6px 0; font-size: 0.95rem; line-height: 1.8;
}
.warning-card {
    background: linear-gradient(135deg, rgba(251,191,36,0.1), rgba(239,68,68,0.08));
    border: 1px solid rgba(251,191,36,0.3); border-radius: 12px; padding: 14px 18px; margin: 6px 0;
}
.success-banner {
    background: linear-gradient(135deg, rgba(52,211,153,0.15), rgba(16,185,129,0.08));
    border: 1px solid rgba(52,211,153,0.4); border-radius: 12px; padding: 16px 20px; margin: 8px 0;
    text-align: center; font-weight: 600; color: #34d399;
}
.tx-row {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px; padding: 12px 16px; margin: 4px 0;
    display: flex; justify-content: space-between; align-items: center;
}
.section-title {
    font-size: 1.15rem; font-weight: 700; color: #c7d2fe;
    border-left: 3px solid #6366f1; padding-left: 10px; margin: 24px 0 14px 0;
}
.budget-bar-bg { background: rgba(255,255,255,0.07); border-radius: 8px; height: 10px; margin-top: 8px; overflow: hidden; }
.stButton > button {
    background: linear-gradient(135deg, #4f46e5, #6366f1) !important;
    color: white !important; border: none !important; border-radius: 10px !important;
    padding: 10px 24px !important; font-weight: 700 !important; width: 100% !important;
    font-size: 0.95rem !important;
}
.save-btn > button {
    background: linear-gradient(135deg, #059669, #10b981) !important;
}
h1, h2, h3 { color: #e2e8f0 !important; }
.stTabs [data-baseweb="tab-list"] { background: rgba(255,255,255,0.03); border-radius: 12px; padding: 4px; }
.stTabs [data-baseweb="tab"] { border-radius: 8px; color: rgba(255,255,255,0.5) !important; }
.stTabs [aria-selected="true"] { background: rgba(99,102,241,0.25) !important; color: #818cf8 !important; }
</style>
""", unsafe_allow_html=True)

# ── DB Init ────────────────────────────────────────────────────
@st.cache_resource
def setup_db():
    try:
        init_db()
        return get_engine()
    except Exception as e:
        st.error(f"❌ Database connection error: {e}")
        return None

engine = setup_db()

# ── Session State Init ─────────────────────────────────────────
# 🔧 FIX: Initialize session state to persist parsed data between button clicks
if "parsed_result" not in st.session_state:
    st.session_state.parsed_result = None
if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = None
if "save_success" not in st.session_state:
    st.session_state.save_success = False

# ── Helpers ────────────────────────────────────────────────────
def save_document(engine, filename, doc_type, summary):
    sql = text("INSERT INTO documents (filename, doc_type, summary) VALUES (:f, :t, :s) RETURNING id")
    with engine.connect() as conn:
        result = conn.execute(sql, {"f": filename, "t": doc_type, "s": summary})
        conn.commit()
        return result.fetchone()[0]

def save_transactions(engine, doc_id, transactions, currency="SEK"):
    sql = text("""
        INSERT INTO transactions (document_id, transaction_date, description, amount, currency, category, transaction_type)
        VALUES (:doc_id, :date, :desc, :amount, :currency, :category, :type)
    """)
    with engine.connect() as conn:
        for tx in transactions:
            try:
                conn.execute(sql, {
                    "doc_id": doc_id, "date": tx.get("date", str(date.today())),
                    "desc": tx.get("description", ""), "amount": float(tx.get("amount", 0)),
                    "currency": tx.get("currency", currency),
                    "category": tx.get("category", "Other"), "type": tx.get("type", "expense"),
                })
            except Exception:
                continue
        conn.commit()

def get_all_transactions(engine):
    try:
        return pd.read_sql("SELECT * FROM transactions ORDER BY transaction_date DESC", engine)
    except:
        return pd.DataFrame()

def get_budgets(engine):
    try:
        return pd.read_sql("SELECT * FROM budgets", engine)
    except:
        return pd.DataFrame()

def generate_insights(df):
    insights, warnings = [], []
    if df.empty:
        return insights, warnings
    expenses = df[df["transaction_type"] == "expense"]
    income = df[df["transaction_type"] == "income"]
    if not expenses.empty:
        top_cat = expenses.groupby("category")["amount"].sum().idxmax()
        top_pct = expenses.groupby("category")["amount"].sum().max() / expenses["amount"].sum() * 100
        icon = CATEGORY_ICONS.get(top_cat, "📦")
        insights.append(f"{icon} Top expense category: **{top_cat}** accounting for **{top_pct:.0f}%** of total spending")
        avg = expenses["amount"].mean()
        insights.append(f"📊 Average transaction amount: **{avg:,.0f} SEK**")
        big = expenses[expenses["amount"] > expenses["amount"].quantile(0.9)]
        if not big.empty:
            warnings.append(f"⚠️ You have **{len(big)} unusually large transactions** — review them!")
    if not income.empty and not expenses.empty:
        ratio = expenses["amount"].sum() / income["amount"].sum() * 100
        if ratio > 80:
            warnings.append(f"🔴 Your expenses are **{ratio:.0f}%** of income — budget is tight!")
        else:
            insights.append(f"✅ Your expenses are **{ratio:.0f}%** of income — healthy financial position")
    return insights, warnings

# ── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💎 Finance AI")
    st.markdown("*Smart Financial Analyzer*")
    st.markdown("---")
    page = st.radio("", ["🏠 Dashboard", "📄 Upload Document", "💳 Transactions", "📊 Analytics", "🎯 Budget", "⚙️ Manage Data"], label_visibility="collapsed")
    st.markdown("---")
    df_all = get_all_transactions(engine) if engine else pd.DataFrame()
    total_in = df_all[df_all["transaction_type"] == "income"]["amount"].sum() if not df_all.empty else 0
    total_out = df_all[df_all["transaction_type"] == "expense"]["amount"].sum() if not df_all.empty else 0
    net = total_in - total_out
    net_color = "#34d399" if net >= 0 else "#f87171"
    st.markdown(f"""
    <div class="kpi-card"><div class="kpi-value income">{total_in:,.0f}</div><div class="kpi-label">Total Income (SEK)</div></div>
    <div class="kpi-card"><div class="kpi-value expense">{total_out:,.0f}</div><div class="kpi-label">Total Expenses (SEK)</div></div>
    <div class="kpi-card"><div class="kpi-value" style="color:{net_color}">{net:+,.0f}</div><div class="kpi-label">Net Balance (SEK)</div></div>
    """, unsafe_allow_html=True)

# ═══ HOME ═══
if page == "🏠 Dashboard":
    st.markdown('<div class="hero"><h1>💎 Finance AI Dashboard</h1><p>Upload your invoices, bank statements, or CSV files — AI analyzes them and gives you instant insights</p></div>', unsafe_allow_html=True)
    df_all = get_all_transactions(engine) if engine else pd.DataFrame()
    if df_all.empty:
        st.markdown('<div class="insight-card" style="text-align:center;padding:40px;"><h2 style="color:#818cf8">👋 Start Here!</h2><p style="color:rgba(255,255,255,0.6)">Go to <strong>📄 Upload Document</strong> and upload your first invoice or CSV file<br>AI will automatically extract all transactions ✨</p></div>', unsafe_allow_html=True)
    else:
        insights, warnings = generate_insights(df_all)
        if insights or warnings:
            st.markdown('<div class="section-title">🧠 Smart Insights</div>', unsafe_allow_html=True)
            for i in insights:
                st.markdown(f'<div class="insight-card">{i}</div>', unsafe_allow_html=True)
            for w in warnings:
                st.markdown(f'<div class="warning-card">{w}</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="section-title">💰 Expense Distribution</div>', unsafe_allow_html=True)
            exp = df_all[df_all["transaction_type"] == "expense"]
            if not exp.empty:
                cat_sum = exp.groupby("category")["amount"].sum().reset_index()
                cat_sum["label"] = cat_sum["category"].map(CATEGORY_ICONS).fillna("📦") + " " + cat_sum["category"]
                colors = [CATEGORY_COLORS.get(c, "#6b7280") for c in cat_sum["category"]]
                fig = px.pie(cat_sum, values="amount", names="label", color_discrete_sequence=colors, hole=0.45)
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", margin=dict(t=10,b=10))
                fig.update_traces(textposition="inside", textinfo="percent", textfont_size=12)
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown('<div class="section-title">📈 Monthly Income & Expenses</div>', unsafe_allow_html=True)
            df_all["transaction_date"] = pd.to_datetime(df_all["transaction_date"])
            monthly = df_all.groupby([df_all["transaction_date"].dt.to_period("M").astype(str), "transaction_type"])["amount"].sum().reset_index()
            monthly.columns = ["month", "type", "amount"]
            fig2 = px.bar(monthly, x="month", y="amount", color="type", barmode="group",
                         color_discrete_map={"income": "#34d399", "expense": "#f87171"})
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", xaxis_title="", yaxis_title="SEK")
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown('<div class="section-title">🕐 Recent Transactions</div>', unsafe_allow_html=True)
        for _, row in df_all.head(8).iterrows():
            icon = CATEGORY_ICONS.get(row["category"], "📦")
            color = "#34d399" if row["transaction_type"] == "income" else "#f87171"
            sign = "+" if row["transaction_type"] == "income" else "-"
            st.markdown(f"""<div class="tx-row">
                <div style="display:flex;gap:12px;align-items:center">
                    <span style="font-size:1.3rem">{icon}</span>
                    <div><div style="font-weight:600">{str(row['description'])[:50]}</div>
                    <div style="font-size:0.78rem;color:rgba(255,255,255,0.4)">{row['category']} · {row['transaction_date']}</div></div>
                </div>
                <div style="font-weight:800;color:{color};font-size:1.05rem">{sign}{row['amount']:,.0f} SEK</div>
            </div>""", unsafe_allow_html=True)

# ═══ UPLOAD ═══
elif page == "📄 Upload Document":
    st.markdown("# 📄 Upload Financial Document")
    st.markdown("*Upload invoices, bank statements, receipts, or CSV files — Gemini AI reads them and extracts transactions automatically*")
    
    uploaded = st.file_uploader("Drag and drop file here", type=["png","jpg","jpeg","webp","pdf","csv"])
    
    # 🔧 FIX: Clear session state when a new file is uploaded
    if uploaded and uploaded.name != st.session_state.uploaded_filename:
        st.session_state.parsed_result = None
        st.session_state.uploaded_filename = uploaded.name
        st.session_state.save_success = False

    if uploaded:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="section-title">📎 Document</div>', unsafe_allow_html=True)
            if uploaded.type == "text/csv":
                st.success(f"📊 CSV File: {uploaded.name}")
                try:
                    csv_preview = pd.read_csv(uploaded)
                    st.dataframe(csv_preview.head(5), use_container_width=True)
                    uploaded.seek(0)
                except:
                    pass
            elif uploaded.type == "application/pdf":
                st.info(f"📄 PDF: {uploaded.name}")
            else:
                st.image(Image.open(uploaded), use_column_width=True, caption=uploaded.name)
        
        with col2:
            st.markdown('<div class="section-title">🤖 AI Analysis</div>', unsafe_allow_html=True)
            
            # ── Step 1: Analyze Button ─────────────────────────────
            if st.button("🚀 Analyze Document Now"):
                st.session_state.save_success = False
                with st.spinner("🧠 Gemini AI is reading the document..."):
                    try:
                        uploaded.seek(0)
                        if uploaded.type == "text/csv":
                            csv_content = uploaded.read().decode('utf-8')
                            parsed = parse_csv_file(csv_content)
                        elif uploaded.type == "application/pdf":
                            parsed = parse_text_document(f"PDF: {uploaded.name}")
                        else:
                            parsed = parse_document(Image.open(uploaded))
                        
                        # 🔧 FIX: Store parsed result in session state so it persists
                        st.session_state.parsed_result = parsed
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
                        st.info("Make sure GEMINI_API_KEY is set in .env or Streamlit secrets")
            
            # ── Step 2: Show Results (from session state) ──────────
            # 🔧 FIX: Render results from session_state, NOT from inside button click
            if st.session_state.parsed_result:
                parsed = st.session_state.parsed_result
                transactions = parsed.get("transactions", [])
                summary = parsed.get("summary", "")
                doc_type = parsed.get("doc_type", "document")
                currency = parsed.get("currency", "SEK")
                
                if transactions:
                    st.success(f"✅ Extracted **{len(transactions)} transactions**!")
                    st.markdown(f'<div class="insight-card">📝 {summary}</div>', unsafe_allow_html=True)
                    preview = pd.DataFrame(transactions)
                    st.dataframe(preview[["date","description","amount","category","type"]], use_container_width=True,
                                column_config={"date":"Date","description":"Description",
                                              "amount":st.column_config.NumberColumn("Amount",format="%.2f"),
                                              "category":"Category","type":"Type"})
                    
                    # ── Step 3: Save Button ────────────────────────────
                    # 🔧 FIX: Save button is OUTSIDE the analyze button block — no nesting
                    if not st.session_state.save_success:
                        st.markdown('<div class="save-btn">', unsafe_allow_html=True)
                        if st.button("💾 Save to Database"):
                            try:
                                doc_id = save_document(engine, uploaded.name, doc_type, summary)
                                save_transactions(engine, doc_id, transactions, currency)
                                st.session_state.save_success = True
                                st.session_state.parsed_result = None  # Clear after saving
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Save failed: {e}")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                else:
                    st.warning("No transactions extracted. Try a clearer image or CSV.")
            
            # ── Show success message after save ────────────────────
            if st.session_state.save_success:
                st.markdown('<div class="success-banner">🎉 Saved successfully! Go to Dashboard to see your data.</div>', unsafe_allow_html=True)
                st.balloons()
                st.session_state.save_success = False

# ═══ TRANSACTIONS ═══
elif page == "💳 Transactions":
    st.markdown("# 💳 Transactions")
    df = get_all_transactions(engine) if engine else pd.DataFrame()
    if df.empty:
        st.info("Upload documents first!")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            tx_type = st.selectbox("Type", ["All","expense","income"])
        with col2:
            cat_filter = st.selectbox("Category", ["All"] + sorted(df["category"].unique().tolist()))
        with col3:
            # Date range filter
            df["transaction_date"] = pd.to_datetime(df["transaction_date"])
            min_date = df["transaction_date"].min().date()
            max_date = df["transaction_date"].max().date()
            date_range = st.date_input("Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

        filtered = df.copy()
        if tx_type != "All":
            filtered = filtered[filtered["transaction_type"] == tx_type]
        if cat_filter != "All":
            filtered = filtered[filtered["category"] == cat_filter]
        if len(date_range) == 2:
            filtered = filtered[
                (filtered["transaction_date"].dt.date >= date_range[0]) &
                (filtered["transaction_date"].dt.date <= date_range[1])
            ]

        # Summary row
        total_shown = filtered["amount"].sum()
        st.markdown(f"*{len(filtered)} transactions · Total: **{total_shown:,.0f} SEK***")

        for _, row in filtered.iterrows():
            icon = CATEGORY_ICONS.get(row["category"], "📦")
            color = "#34d399" if row["transaction_type"] == "income" else "#f87171"
            sign = "+" if row["transaction_type"] == "income" else "-"
            st.markdown(f"""<div class="tx-row">
                <div style="display:flex;gap:12px;align-items:center">
                    <span style="font-size:1.3rem">{icon}</span>
                    <div><div style="font-weight:600">{str(row['description'])[:55]}</div>
                    <div style="font-size:0.78rem;color:rgba(255,255,255,0.4)">{row['category']} · {row['transaction_date'].strftime('%Y-%m-%d') if hasattr(row['transaction_date'], 'strftime') else row['transaction_date']}</div></div>
                </div>
                <div style="font-weight:800;color:{color};font-size:1.1rem">{sign}{row['amount']:,.0f} SEK</div>
            </div>""", unsafe_allow_html=True)
        
        st.markdown("---")
        csv = filtered.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Export CSV", csv, "transactions.csv", "text/csv")

# ═══ ANALYTICS ═══
elif page == "📊 Analytics":
    st.markdown("# 📊 Advanced Analytics")
    df = get_all_transactions(engine) if engine else pd.DataFrame()
    if df.empty:
        st.info("Upload documents first!")
    else:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"])
        expenses = df[df["transaction_type"] == "expense"]
        if not expenses.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<div class="section-title">📅 Weekly Expenses</div>', unsafe_allow_html=True)
                weekly = expenses.copy()
                weekly["week"] = weekly["transaction_date"].dt.to_period("W").astype(str)
                w_sum = weekly.groupby("week")["amount"].sum().reset_index()
                fig = px.line(w_sum, x="week", y="amount", markers=True, color_discrete_sequence=["#818cf8"])
                fig.update_traces(fill="tozeroy", fillcolor="rgba(99,102,241,0.1)")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", xaxis_title="", yaxis_title="SEK")
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.markdown('<div class="section-title">🏆 Top Spending Categories</div>', unsafe_allow_html=True)
                cat_sum = expenses.groupby("category")["amount"].sum().sort_values().reset_index()
                cat_sum["label"] = cat_sum["category"].map(CATEGORY_ICONS).fillna("📦") + " " + cat_sum["category"]
                fig2 = px.bar(cat_sum, x="amount", y="label", orientation="h",
                             color="category", color_discrete_map=CATEGORY_COLORS)
                fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", showlegend=False, xaxis_title="SEK", yaxis_title="")
                st.plotly_chart(fig2, use_container_width=True)

            st.markdown('<div class="section-title">📆 Spending by Day of Week</div>', unsafe_allow_html=True)
            days_en = {0:"Monday",1:"Tuesday",2:"Wednesday",3:"Thursday",4:"Friday",5:"Saturday",6:"Sunday"}
            exp2 = expenses.copy()
            exp2["day_num"] = exp2["transaction_date"].dt.dayofweek
            exp2["day_name"] = exp2["day_num"].map(days_en)
            day_sum = exp2.groupby(["day_num","day_name"])["amount"].sum().reset_index().sort_values("day_num")
            fig3 = px.bar(day_sum, x="day_name", y="amount", color="amount", color_continuous_scale=["#4f46e5","#f87171"])
            fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", coloraxis_showscale=False, xaxis_title="", yaxis_title="SEK")
            st.plotly_chart(fig3, use_container_width=True)

            # NEW: Monthly trend table
            st.markdown('<div class="section-title">📋 Monthly Summary Table</div>', unsafe_allow_html=True)
            df["month"] = df["transaction_date"].dt.to_period("M").astype(str)
            monthly_pivot = df.groupby(["month","transaction_type"])["amount"].sum().unstack(fill_value=0).reset_index()
            if "income" in monthly_pivot.columns and "expense" in monthly_pivot.columns:
                monthly_pivot["net"] = monthly_pivot["income"] - monthly_pivot["expense"]
                monthly_pivot.columns.name = None
                st.dataframe(monthly_pivot.rename(columns={"month":"Month","income":"Income (SEK)","expense":"Expenses (SEK)","net":"Net (SEK)"}),
                            use_container_width=True, hide_index=True)

# ═══ BUDGET ═══
elif page == "🎯 Budget":
    st.markdown("# 🎯 Monthly Budget Management")
    categories = ["Food","Transport","Shopping","Health","Education","Entertainment","Housing","Other"]
    st.markdown('<div class="section-title">Set Your Monthly Limits</div>', unsafe_allow_html=True)
    budgets = {}
    cols = st.columns(2)
    for i, cat in enumerate(categories):
        with cols[i % 2]:
            icon = CATEGORY_ICONS.get(cat, "📦")
            budgets[cat] = st.number_input(f"{icon} {cat}", min_value=0.0, step=100.0, format="%.0f", key=f"budget_{cat}")
    if st.button("💾 Save Budget"):
        sql = text("INSERT INTO budgets (category, monthly_limit) VALUES (:cat, :limit) ON CONFLICT (category) DO UPDATE SET monthly_limit = EXCLUDED.monthly_limit")
        with engine.connect() as conn:
            for cat, limit in budgets.items():
                if limit > 0:
                    conn.execute(sql, {"cat": cat, "limit": limit})
            conn.commit()
        st.success("✅ Budget saved!")

    df = get_all_transactions(engine) if engine else pd.DataFrame()
    budget_df = get_budgets(engine)
    if not df.empty and not budget_df.empty:
        st.markdown('<div class="section-title">📊 Your Progress This Month</div>', unsafe_allow_html=True)
        df["transaction_date"] = pd.to_datetime(df["transaction_date"])
        this_month = df[df["transaction_date"].dt.month == date.today().month]
        expenses_month = this_month[this_month["transaction_type"] == "expense"].groupby("category")["amount"].sum()
        for _, brow in budget_df.iterrows():
            cat = brow["category"]
            limit = float(brow["monthly_limit"])
            spent = float(expenses_month.get(cat, 0))
            pct = min(spent / limit * 100, 100) if limit > 0 else 0
            bar_color = "#34d399" if pct < 70 else "#fbbf24" if pct < 90 else "#f87171"
            icon = CATEGORY_ICONS.get(cat, "📦")
            st.markdown(f"""
            <div style="margin:12px 0">
                <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                    <span style="font-weight:600">{icon} {cat}</span>
                    <span style="color:rgba(255,255,255,0.5)">{spent:,.0f} / {limit:,.0f} SEK</span>
                </div>
                <div class="budget-bar-bg">
                    <div style="height:10px;width:{pct}%;background:{bar_color};border-radius:8px;transition:width 0.5s"></div>
                </div>
            </div>""", unsafe_allow_html=True)

# ═══ MANAGE DATA ═══
elif page == "⚙️ Manage Data":
    st.markdown("# ⚙️ Manage Data")
    df = get_all_transactions(engine) if engine else pd.DataFrame()
    
    st.markdown('<div class="section-title">📂 Uploaded Documents</div>', unsafe_allow_html=True)
    try:
        docs_df = pd.read_sql("SELECT id, filename, doc_type, upload_date, summary FROM documents ORDER BY upload_date DESC", engine)
        if docs_df.empty:
            st.info("No documents uploaded yet.")
        else:
            for _, doc in docs_df.iterrows():
                tx_count = len(df[df["document_id"] == doc["id"]]) if not df.empty else 0
                with st.expander(f"📄 {doc['filename']} — {tx_count} transactions · {str(doc['upload_date'])[:10]}"):
                    st.write(f"**Type:** {doc['doc_type']}")
                    st.write(f"**Summary:** {doc['summary']}")
                    if st.button(f"🗑️ Delete this document", key=f"del_{doc['id']}"):
                        with engine.connect() as conn:
                            conn.execute(text("DELETE FROM documents WHERE id = :id"), {"id": int(doc["id"])})
                            conn.commit()
                        st.success("Deleted!")
                        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")
    
    st.markdown('<div class="section-title">➕ Add Manual Transaction</div>', unsafe_allow_html=True)
    with st.form("manual_tx"):
        c1, c2 = st.columns(2)
        with c1:
            m_date = st.date_input("Date", value=date.today())
            m_desc = st.text_input("Description")
            m_amount = st.number_input("Amount", min_value=0.0, step=10.0)
        with c2:
            m_cat = st.selectbox("Category", list(CATEGORY_ICONS.keys()))
            m_type = st.selectbox("Type", ["expense", "income"])
        if st.form_submit_button("➕ Add Transaction"):
            try:
                # Use a generic doc_id = 0 or create a "Manual" doc
                try:
                    doc_id = save_document(engine, "Manual Entry", "manual", "Manually added transaction")
                except:
                    doc_id = 1
                save_transactions(engine, doc_id, [{
                    "date": str(m_date), "description": m_desc,
                    "amount": m_amount, "category": m_cat, "type": m_type
                }])
                st.success("✅ Transaction added!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
