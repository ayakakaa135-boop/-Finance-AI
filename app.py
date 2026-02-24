"""
💎 Finance AI — Smart Financial Document Analyzer
✨ v2.0: PDF OCR · Multi-Currency · AI Chat · PDF Reports · Budget Alerts
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image
from datetime import date
from sqlalchemy import text
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_engine, init_db
from ai_parser import (
    parse_document, parse_text_document, parse_pdf_file,
    parse_csv_file, chat_with_finances,
    convert_transactions_to_sek, get_exchange_rate,
    CATEGORY_ICONS, CATEGORY_COLORS
)
from pdf_report import generate_pdf_report

# ── Page Config ────────────────────────────────────────────────
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
    content:''; position:absolute; bottom:0; left:0; right:0;
    height:2px; background: linear-gradient(90deg, #6366f1, #34d399);
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
.chat-bubble-user {
    background: rgba(99,102,241,0.2); border: 1px solid rgba(99,102,241,0.3);
    border-radius: 16px 16px 4px 16px; padding: 12px 16px; margin: 8px 0 8px 40px;
}
.chat-bubble-ai {
    background: rgba(52,211,153,0.08); border: 1px solid rgba(52,211,153,0.2);
    border-radius: 16px 16px 16px 4px; padding: 12px 16px; margin: 8px 40px 8px 0;
}
.currency-badge {
    display: inline-block; background: rgba(99,102,241,0.2);
    border: 1px solid rgba(99,102,241,0.4); border-radius: 6px;
    padding: 2px 8px; font-size: 0.75rem; color: #818cf8; margin-left: 8px;
}
.stButton > button {
    background: linear-gradient(135deg, #4f46e5, #6366f1) !important;
    color: white !important; border: none !important; border-radius: 10px !important;
    padding: 10px 24px !important; font-weight: 700 !important; width: 100% !important;
}
h1,h2,h3 { color: #e2e8f0 !important; }
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
        st.error(f"❌ Database error: {e}")
        return None

engine = setup_db()

# ── Session State ──────────────────────────────────────────────
for key, default in [
    ("parsed_result", None), ("uploaded_filename", None),
    ("save_success", False), ("chat_history", []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── DB Helpers ─────────────────────────────────────────────────
def save_document(engine, filename, doc_type, summary):
    sql = text("INSERT INTO documents (filename, doc_type, summary) VALUES (:f,:t,:s) RETURNING id")
    with engine.connect() as conn:
        result = conn.execute(sql, {"f": filename, "t": doc_type, "s": summary})
        conn.commit()
        return result.fetchone()[0]

def save_transactions(engine, doc_id, transactions, currency="SEK"):
    sql = text("""INSERT INTO transactions
        (document_id, transaction_date, description, amount, currency, category, transaction_type)
        VALUES (:doc_id,:date,:desc,:amount,:currency,:category,:type)""")
    with engine.connect() as conn:
        for tx in transactions:
            try:
                conn.execute(sql, {
                    "doc_id": doc_id,
                    "date": tx.get("date", str(date.today())),
                    "desc": tx.get("description", ""),
                    "amount": float(tx.get("amount", 0)),
                    "currency": tx.get("original_currency", currency),
                    "category": tx.get("category", "Other"),
                    "type": tx.get("type", "expense"),
                })
            except Exception:
                continue
        conn.commit()

def get_all_transactions(engine):
    try:
        return pd.read_sql("SELECT * FROM transactions ORDER BY transaction_date DESC", engine)
    except Exception:
        return pd.DataFrame()

def get_budgets(engine):
    try:
        return pd.read_sql("SELECT * FROM budgets", engine)
    except Exception:
        return pd.DataFrame()

# ── Insights + Budget Alerts ───────────────────────────────────
def generate_insights(df, engine=None):
    insights, warnings = [], []
    if df.empty:
        return insights, warnings

    expenses = df[df["transaction_type"] == "expense"]
    income   = df[df["transaction_type"] == "income"]

    if not expenses.empty:
        top_cat = expenses.groupby("category")["amount"].sum().idxmax()
        top_pct = expenses.groupby("category")["amount"].sum().max() / expenses["amount"].sum() * 100
        icon = CATEGORY_ICONS.get(top_cat, "📦")
        insights.append(f"{icon} Top category: **{top_cat}** — **{top_pct:.0f}%** of spending")
        insights.append(f"📊 Average transaction: **{expenses['amount'].mean():,.0f} SEK**")
        big = expenses[expenses["amount"] > expenses["amount"].quantile(0.9)]
        if not big.empty:
            warnings.append(f"⚠️ **{len(big)} unusually large transactions** — review them!")

    if not income.empty and not expenses.empty:
        ratio = expenses["amount"].sum() / income["amount"].sum() * 100
        if ratio > 80:
            warnings.append(f"🔴 Expenses are **{ratio:.0f}%** of income — budget is tight!")
        else:
            insights.append(f"✅ Expenses are **{ratio:.0f}%** of income — healthy balance")

    # ✨ Budget alerts
    if engine:
        budget_df = get_budgets(engine)
        if not budget_df.empty and not expenses.empty:
            df_c = df.copy()
            df_c["transaction_date"] = pd.to_datetime(df_c["transaction_date"], errors="coerce")
            this_month = df_c[df_c["transaction_date"].dt.month == date.today().month]
            exp_month  = this_month[this_month["transaction_type"] == "expense"].groupby("category")["amount"].sum()
            for _, b in budget_df.iterrows():
                cat   = b["category"]
                limit = float(b["monthly_limit"])
                spent = float(exp_month.get(cat, 0))
                pct   = spent / limit * 100 if limit > 0 else 0
                icon  = CATEGORY_ICONS.get(cat, "📦")
                if pct >= 100:
                    warnings.append(f"🚨 {icon} **{cat}**: OVER budget! {spent:,.0f} / {limit:,.0f} SEK")
                elif pct >= 80:
                    warnings.append(f"🔔 {icon} **{cat}**: {pct:.0f}% used — {limit-spent:,.0f} SEK left")

    return insights, warnings

# ── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💎 Finance AI")
    st.markdown("*v2.0 · AI-Powered*")
    st.markdown("---")
    page = st.radio("Navigation", [
        "🏠 Dashboard", "📄 Upload Document", "💳 Transactions",
        "📊 Analytics", "🎯 Budget", "💬 AI Chat", "⚙️ Manage Data"
    ], label_visibility="collapsed")
    st.markdown("---")
    df_all = get_all_transactions(engine) if engine else pd.DataFrame()
    total_in  = df_all[df_all["transaction_type"] == "income"]["amount"].sum()  if not df_all.empty else 0
    total_out = df_all[df_all["transaction_type"] == "expense"]["amount"].sum() if not df_all.empty else 0
    net = total_in - total_out
    net_color = "#34d399" if net >= 0 else "#f87171"
    st.markdown(f"""
    <div class="kpi-card"><div class="kpi-value income">{total_in:,.0f}</div><div class="kpi-label">Total Income (SEK)</div></div>
    <div class="kpi-card"><div class="kpi-value expense">{total_out:,.0f}</div><div class="kpi-label">Total Expenses (SEK)</div></div>
    <div class="kpi-card"><div class="kpi-value" style="color:{net_color}">{net:+,.0f}</div><div class="kpi-label">Net Balance (SEK)</div></div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 🏠 DASHBOARD
# ══════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.markdown('<div class="hero"><h1>💎 Finance AI Dashboard</h1><p>AI-powered · PDF OCR · Multi-currency · Smart insights · PDF reports</p></div>', unsafe_allow_html=True)
    df_all = get_all_transactions(engine) if engine else pd.DataFrame()

    if df_all.empty:
        st.markdown('<div class="insight-card" style="text-align:center;padding:40px;"><h2 style="color:#818cf8">👋 Start Here!</h2><p style="color:rgba(255,255,255,0.6)">Go to <strong>📄 Upload Document</strong> and upload your first invoice, PDF, or CSV ✨</p></div>', unsafe_allow_html=True)
    else:
        insights, warnings = generate_insights(df_all, engine)
        if insights or warnings:
            st.markdown('<div class="section-title">🧠 Smart Insights & Alerts</div>', unsafe_allow_html=True)
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
                fig = px.pie(cat_sum, values="amount", names="label",
                             color_discrete_sequence=[CATEGORY_COLORS.get(c, "#6b7280") for c in cat_sum["category"]], hole=0.45)
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", margin=dict(t=10,b=10))
                fig.update_traces(textposition="inside", textinfo="percent", textfont_size=12)
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown('<div class="section-title">📈 Monthly Income vs Expenses</div>', unsafe_allow_html=True)
            df_all["transaction_date"] = pd.to_datetime(df_all["transaction_date"], errors="coerce")
            monthly = df_all.groupby([df_all["transaction_date"].dt.to_period("M").astype(str), "transaction_type"])["amount"].sum().reset_index()
            monthly.columns = ["month","type","amount"]
            fig2 = px.bar(monthly, x="month", y="amount", color="type", barmode="group",
                          color_discrete_map={"income":"#34d399","expense":"#f87171"})
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", xaxis_title="", yaxis_title="SEK")
            st.plotly_chart(fig2, use_container_width=True)

        # ✨ PDF Report Export
        st.markdown('<div class="section-title">📥 Export PDF Report</div>', unsafe_allow_html=True)
        month_options = sorted(df_all["transaction_date"].dt.to_period("M").astype(str).unique(), reverse=True)
        col_sel, col_btn = st.columns([2, 1])
        with col_sel:
            selected_month = st.selectbox("Select period", ["All time"] + list(month_options))
        with col_btn:
            st.write("")
            st.write("")
            if st.button("📄 Generate PDF"):
                with st.spinner("Building report..."):
                    try:
                        df_report = df_all.copy()
                        if selected_month != "All time":
                            df_report["_m"] = df_report["transaction_date"].dt.to_period("M").astype(str)
                            df_report = df_report[df_report["_m"] == selected_month]
                        pdf_bytes = generate_pdf_report(df_report, selected_month)
                        st.download_button(
                            label="⬇️ Download PDF",
                            data=pdf_bytes,
                            file_name=f"finance_report_{selected_month.replace(' ','_')}.pdf",
                            mime="application/pdf",
                        )
                    except Exception as e:
                        st.error(f"Report error: {e}")

        st.markdown('<div class="section-title">🕐 Recent Transactions</div>', unsafe_allow_html=True)
        for _, row in df_all.head(8).iterrows():
            icon  = CATEGORY_ICONS.get(row["category"], "📦")
            color = "#34d399" if row["transaction_type"] == "income" else "#f87171"
            sign  = "+" if row["transaction_type"] == "income" else "-"
            st.markdown(f"""<div class="tx-row">
                <div style="display:flex;gap:12px;align-items:center">
                    <span style="font-size:1.3rem">{icon}</span>
                    <div><div style="font-weight:600">{str(row['description'])[:50]}</div>
                    <div style="font-size:0.78rem;color:rgba(255,255,255,0.4)">{row['category']} · {row['transaction_date']}</div></div>
                </div>
                <div style="font-weight:800;color:{color};font-size:1.05rem">{sign}{row['amount']:,.0f} SEK</div>
            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 📄 UPLOAD
# ══════════════════════════════════════════════════════════════
elif page == "📄 Upload Document":
    st.markdown("# 📄 Upload Financial Document")
    st.markdown("*Images · PDF with OCR · CSV · Multi-currency auto-conversion*")

    uploaded = st.file_uploader("Drop file here", type=["png","jpg","jpeg","webp","pdf","csv"])

    if uploaded and uploaded.name != st.session_state.uploaded_filename:
        st.session_state.parsed_result     = None
        st.session_state.uploaded_filename = uploaded.name
        st.session_state.save_success      = False

    if uploaded:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="section-title">📎 Preview</div>', unsafe_allow_html=True)
            if uploaded.type == "text/csv":
                st.success(f"📊 CSV: {uploaded.name}")
                try:
                    df_prev = pd.read_csv(uploaded); uploaded.seek(0)
                    st.dataframe(df_prev.head(5), use_container_width=True)
                except Exception:
                    pass
            elif uploaded.type == "application/pdf":
                st.info(f"📄 PDF: {uploaded.name}\n\n✨ OCR will extract text automatically")
            else:
                st.image(Image.open(uploaded), use_column_width=True, caption=uploaded.name)

        with col2:
            st.markdown('<div class="section-title">🤖 AI Analysis</div>', unsafe_allow_html=True)

            # Currency selector
            c1, c2 = st.columns(2)
            with c1:
                source_currency = st.selectbox("Currency", ["SEK","USD","EUR","GBP","NOK","DKK","JPY","CHF"])
            with c2:
                if source_currency != "SEK":
                    try:
                        rate = get_exchange_rate(source_currency, "SEK")
                        st.metric("Rate", f"1 {source_currency} = {rate:.2f} SEK")
                    except Exception:
                        st.caption("Fetching rate...")

            if st.button("🚀 Analyze Document"):
                st.session_state.save_success = False
                with st.spinner("🧠 Gemini AI is reading..."):
                    try:
                        uploaded.seek(0)
                        if uploaded.type == "text/csv":
                            parsed = parse_csv_file(uploaded.read().decode("utf-8"))
                        elif uploaded.type == "application/pdf":
                            parsed = parse_pdf_file(uploaded.read())   # ✨ Real OCR
                        else:
                            parsed = parse_document(Image.open(uploaded))

                        # ✨ Auto convert currency
                        doc_currency = parsed.get("currency", source_currency)
                        conv_currency = doc_currency if doc_currency != "SEK" else source_currency
                        if conv_currency != "SEK":
                            parsed["transactions"] = convert_transactions_to_sek(parsed["transactions"], conv_currency)
                            parsed["converted_from"] = conv_currency

                        st.session_state.parsed_result = parsed
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

            if st.session_state.parsed_result:
                parsed       = st.session_state.parsed_result
                transactions = parsed.get("transactions", [])
                summary      = parsed.get("summary", "")
                doc_type     = parsed.get("doc_type", "document")
                currency     = parsed.get("currency", "SEK")
                converted    = parsed.get("converted_from")

                if transactions:
                    msg = f"✅ **{len(transactions)} transactions**"
                    if converted:
                        msg += f" — converted from **{converted}** to SEK"
                    st.success(msg)
                    st.markdown(f'<div class="insight-card">📝 {summary}</div>', unsafe_allow_html=True)
                    preview = pd.DataFrame(transactions)
                    cols_show = [c for c in ["date","description","amount","original_amount","category","type"] if c in preview.columns]
                    st.dataframe(preview[cols_show], use_container_width=True,
                                 column_config={"amount": st.column_config.NumberColumn("Amount (SEK)", format="%.2f"),
                                                "original_amount": st.column_config.NumberColumn(f"Orig ({converted})", format="%.2f")})

                    if not st.session_state.save_success:
                        if st.button("💾 Save to Database"):
                            try:
                                doc_id = save_document(engine, uploaded.name, doc_type, summary)
                                save_transactions(engine, doc_id, transactions, currency)
                                st.session_state.save_success  = True
                                st.session_state.parsed_result = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Save failed: {e}")
                else:
                    st.warning("No transactions found. Try a clearer file.")

            if st.session_state.save_success:
                st.markdown('<div class="success-banner">🎉 Saved! Go to Dashboard.</div>', unsafe_allow_html=True)
                st.balloons()
                st.session_state.save_success = False

# ══════════════════════════════════════════════════════════════
# 💳 TRANSACTIONS
# ══════════════════════════════════════════════════════════════
elif page == "💳 Transactions":
    st.markdown("# 💳 Transactions")
    df = get_all_transactions(engine) if engine else pd.DataFrame()
    if df.empty:
        st.info("Upload documents first!")
    else:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
        c1, c2, c3 = st.columns(3)
        with c1: tx_type = st.selectbox("Type", ["All","expense","income"])
        with c2: cat_filter = st.selectbox("Category", ["All"] + sorted(df["category"].unique().tolist()))
        with c3:
            min_d = df["transaction_date"].min().date()
            max_d = df["transaction_date"].max().date()
            date_range = st.date_input("Range", value=(min_d, max_d), min_value=min_d, max_value=max_d)

        filtered = df.copy()
        if tx_type != "All":    filtered = filtered[filtered["transaction_type"] == tx_type]
        if cat_filter != "All": filtered = filtered[filtered["category"] == cat_filter]
        if len(date_range) == 2:
            filtered = filtered[(filtered["transaction_date"].dt.date >= date_range[0]) &
                                 (filtered["transaction_date"].dt.date <= date_range[1])]

        st.markdown(f"*{len(filtered)} transactions · Total: **{filtered['amount'].sum():,.0f} SEK***")
        for _, row in filtered.iterrows():
            icon  = CATEGORY_ICONS.get(row["category"], "📦")
            color = "#34d399" if row["transaction_type"] == "income" else "#f87171"
            sign  = "+" if row["transaction_type"] == "income" else "-"
            tx_date = row["transaction_date"].strftime("%Y-%m-%d") if hasattr(row["transaction_date"], "strftime") else str(row["transaction_date"])[:10]
            st.markdown(f"""<div class="tx-row">
                <div style="display:flex;gap:12px;align-items:center">
                    <span style="font-size:1.3rem">{icon}</span>
                    <div><div style="font-weight:600">{str(row['description'])[:55]}</div>
                    <div style="font-size:0.78rem;color:rgba(255,255,255,0.4)">{row['category']} · {tx_date}</div></div>
                </div>
                <div style="font-weight:800;color:{color};font-size:1.1rem">{sign}{row['amount']:,.0f} SEK</div>
            </div>""", unsafe_allow_html=True)
        st.markdown("---")
        st.download_button("⬇️ Export CSV", filtered.to_csv(index=False).encode("utf-8-sig"), "transactions.csv", "text/csv")

# ══════════════════════════════════════════════════════════════
# 📊 ANALYTICS
# ══════════════════════════════════════════════════════════════
elif page == "📊 Analytics":
    st.markdown("# 📊 Analytics")
    df = get_all_transactions(engine) if engine else pd.DataFrame()
    if df.empty:
        st.info("Upload documents first!")
    else:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
        expenses = df[df["transaction_type"] == "expense"]
        if not expenses.empty:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<div class="section-title">📅 Weekly Spending</div>', unsafe_allow_html=True)
                w = expenses.copy()
                w["week"] = w["transaction_date"].dt.to_period("W").astype(str)
                w_sum = w.groupby("week")["amount"].sum().reset_index()
                fig = px.line(w_sum, x="week", y="amount", markers=True, color_discrete_sequence=["#818cf8"])
                fig.update_traces(fill="tozeroy", fillcolor="rgba(99,102,241,0.1)")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", xaxis_title="", yaxis_title="SEK")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.markdown('<div class="section-title">🏆 Top Categories</div>', unsafe_allow_html=True)
                cat_sum = expenses.groupby("category")["amount"].sum().sort_values().reset_index()
                cat_sum["label"] = cat_sum["category"].map(CATEGORY_ICONS).fillna("📦") + " " + cat_sum["category"]
                fig2 = px.bar(cat_sum, x="amount", y="label", orientation="h", color="category", color_discrete_map=CATEGORY_COLORS)
                fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", showlegend=False, xaxis_title="SEK", yaxis_title="")
                st.plotly_chart(fig2, use_container_width=True)

            st.markdown('<div class="section-title">📆 By Day of Week</div>', unsafe_allow_html=True)
            days = {0:"Monday",1:"Tuesday",2:"Wednesday",3:"Thursday",4:"Friday",5:"Saturday",6:"Sunday"}
            ex2 = expenses.copy()
            ex2["day_num"]  = ex2["transaction_date"].dt.dayofweek
            ex2["day_name"] = ex2["day_num"].map(days)
            day_sum = ex2.groupby(["day_num","day_name"])["amount"].sum().reset_index().sort_values("day_num")
            fig3 = px.bar(day_sum, x="day_name", y="amount", color="amount", color_continuous_scale=["#4f46e5","#f87171"])
            fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", coloraxis_showscale=False, xaxis_title="", yaxis_title="SEK")
            st.plotly_chart(fig3, use_container_width=True)

            st.markdown('<div class="section-title">📋 Monthly Summary</div>', unsafe_allow_html=True)
            df["month"] = df["transaction_date"].dt.to_period("M").astype(str)
            mp = df.groupby(["month","transaction_type"])["amount"].sum().unstack(fill_value=0).reset_index()
            if "income" in mp.columns and "expense" in mp.columns:
                mp["net"] = mp["income"] - mp["expense"]
                mp.columns.name = None
                st.dataframe(mp.rename(columns={"month":"Month","income":"Income (SEK)","expense":"Expenses (SEK)","net":"Net (SEK)"}),
                             use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════
# 🎯 BUDGET
# ══════════════════════════════════════════════════════════════
elif page == "🎯 Budget":
    st.markdown("# 🎯 Budget")
    categories = ["Food","Transport","Shopping","Health","Education","Entertainment","Housing","Other"]
    st.markdown('<div class="section-title">Set Monthly Limits</div>', unsafe_allow_html=True)
    budgets = {}
    cols = st.columns(2)
    for i, cat in enumerate(categories):
        with cols[i % 2]:
            budgets[cat] = st.number_input(f"{CATEGORY_ICONS.get(cat,'📦')} {cat}", min_value=0.0, step=100.0, format="%.0f", key=f"b_{cat}")

    if st.button("💾 Save Budget"):
        sql = text("INSERT INTO budgets (category, monthly_limit) VALUES (:cat,:limit) ON CONFLICT (category) DO UPDATE SET monthly_limit = EXCLUDED.monthly_limit")
        with engine.connect() as conn:
            for cat, limit in budgets.items():
                if limit > 0:
                    conn.execute(sql, {"cat": cat, "limit": limit})
            conn.commit()
        st.success("✅ Saved!")

    df = get_all_transactions(engine) if engine else pd.DataFrame()
    budget_df = get_budgets(engine)
    if not df.empty and not budget_df.empty:
        st.markdown('<div class="section-title">📊 This Month</div>', unsafe_allow_html=True)
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
        this_month = df[df["transaction_date"].dt.month == date.today().month]
        exp_month  = this_month[this_month["transaction_type"] == "expense"].groupby("category")["amount"].sum()
        for _, brow in budget_df.iterrows():
            cat   = brow["category"]
            limit = float(brow["monthly_limit"])
            spent = float(exp_month.get(cat, 0))
            pct   = min(spent / limit * 100, 100) if limit > 0 else 0
            bar_c = "#34d399" if pct < 70 else "#fbbf24" if pct < 90 else "#f87171"
            icon  = CATEGORY_ICONS.get(cat, "📦")
            alert = " 🚨" if spent > limit else (" ⚠️" if pct >= 80 else "")
            st.markdown(f"""<div style="margin:12px 0">
                <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                    <span style="font-weight:600">{icon} {cat}{alert}</span>
                    <span style="color:rgba(255,255,255,0.5)">{spent:,.0f} / {limit:,.0f} SEK · {pct:.0f}%</span>
                </div>
                <div class="budget-bar-bg"><div style="height:10px;width:{pct}%;background:{bar_c};border-radius:8px"></div></div>
            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 💬 AI CHAT  ✨ NEW
# ══════════════════════════════════════════════════════════════
elif page == "💬 AI Chat":
    st.markdown("# 💬 AI Financial Assistant")
    st.markdown("*Ask anything about your finances in Arabic or English*")

    df = get_all_transactions(engine) if engine else pd.DataFrame()
    if df.empty:
        st.markdown('<div class="warning-card">⚠️ No data yet. Upload documents first!</div>', unsafe_allow_html=True)
    else:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
        expenses = df[df["transaction_type"] == "expense"]
        income   = df[df["transaction_type"] == "income"]
        cat_breakdown = expenses.groupby("category")["amount"].sum().to_dict() if not expenses.empty else {}

        financial_context = f"""
Total income: {income['amount'].sum():,.0f} SEK
Total expenses: {expenses['amount'].sum():,.0f} SEK
Net balance: {income['amount'].sum() - expenses['amount'].sum():,.0f} SEK
Number of transactions: {len(df)}

Expenses by category:
{chr(10).join(f"  - {cat}: {amt:,.0f} SEK" for cat, amt in sorted(cat_breakdown.items(), key=lambda x: -x[1]))}

Recent 10 transactions:
{df.head(10)[['transaction_date','description','amount','category','transaction_type']].to_string(index=False)}
"""

        # Example questions
        st.markdown('<div class="section-title">💡 Quick Questions</div>', unsafe_allow_html=True)
        examples = [
            "Where am I spending the most?",
            "Am I saving enough this month?",
            "Give me 3 tips to save money",
            "Which category should I cut?",
            "وين راحت معظم فلوسي؟",
            "كيف وضعي المالي؟",
        ]
        cols = st.columns(3)
        for i, ex in enumerate(examples):
            with cols[i % 3]:
                if st.button(ex, key=f"q{i}"):
                    st.session_state.chat_history.append(("user", ex))
                    with st.spinner("Thinking..."):
                        resp = chat_with_finances(ex, financial_context, st.session_state.chat_history[:-1])
                    st.session_state.chat_history.append(("ai", resp))
                    st.rerun()

        # Chat display
        st.markdown('<div class="section-title">💬 Conversation</div>', unsafe_allow_html=True)
        if not st.session_state.chat_history:
            st.markdown('<div class="insight-card" style="text-align:center;color:rgba(255,255,255,0.4)">Ask a question above or type below 👇</div>', unsafe_allow_html=True)

        for role, msg in st.session_state.chat_history:
            css = "chat-bubble-user" if role == "user" else "chat-bubble-ai"
            prefix = "👤" if role == "user" else "🤖"
            st.markdown(f'<div class="{css}">{prefix} {msg}</div>', unsafe_allow_html=True)

        user_input = st.chat_input("Ask about your finances...")
        if user_input:
            st.session_state.chat_history.append(("user", user_input))
            with st.spinner("🧠 Analyzing..."):
                try:
                    resp = chat_with_finances(user_input, financial_context, st.session_state.chat_history[:-1])
                    st.session_state.chat_history.append(("ai", resp))
                except Exception as e:
                    st.session_state.chat_history.append(("ai", f"Error: {e}"))
            st.rerun()

        if st.session_state.chat_history:
            if st.button("🗑️ Clear Chat"):
                st.session_state.chat_history = []
                st.rerun()

# ══════════════════════════════════════════════════════════════
# ⚙️ MANAGE DATA
# ══════════════════════════════════════════════════════════════
elif page == "⚙️ Manage Data":
    st.markdown("# ⚙️ Manage Data")
    df = get_all_transactions(engine) if engine else pd.DataFrame()

    st.markdown('<div class="section-title">📂 Documents</div>', unsafe_allow_html=True)
    try:
        docs_df = pd.read_sql("SELECT id, filename, doc_type, upload_date, summary FROM documents ORDER BY upload_date DESC", engine)
        if docs_df.empty:
            st.info("No documents yet.")
        else:
            for _, doc in docs_df.iterrows():
                tx_count = len(df[df["document_id"] == doc["id"]]) if not df.empty else 0
                with st.expander(f"📄 {doc['filename']} — {tx_count} tx · {str(doc['upload_date'])[:10]}"):
                    st.write(f"**Type:** {doc['doc_type']}  |  **Summary:** {doc['summary']}")
                    if st.button("🗑️ Delete", key=f"del_{doc['id']}"):
                        with engine.connect() as conn:
                            conn.execute(text("DELETE FROM documents WHERE id = :id"), {"id": int(doc["id"])})
                            conn.commit()
                        st.success("Deleted!")
                        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

    st.markdown('<div class="section-title">➕ Manual Transaction</div>', unsafe_allow_html=True)
    with st.form("manual_tx"):
        c1, c2 = st.columns(2)
        with c1:
            m_date   = st.date_input("Date", value=date.today())
            m_desc   = st.text_input("Description")
            m_amount = st.number_input("Amount (SEK)", min_value=0.0, step=10.0)
        with c2:
            m_cat  = st.selectbox("Category", list(CATEGORY_ICONS.keys()))
            m_type = st.selectbox("Type", ["expense","income"])
        if st.form_submit_button("➕ Add"):
            try:
                doc_id = save_document(engine, "Manual Entry", "manual", "Manually added")
                save_transactions(engine, doc_id, [{"date": str(m_date), "description": m_desc, "amount": m_amount, "category": m_cat, "type": m_type}])
                st.success("✅ Added!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
