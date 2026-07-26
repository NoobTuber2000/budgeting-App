import json
from datetime import datetime
import os
import pandas as pd
import streamlit as st

# Define local data persistence files
DATA_FILE = "budget_data.json"
EXPENSES_FILE = "expenses_data.json"
SAVINGS_FILE = "savings_goals.json"
HISTORY_FILE = "historical_logs.json"
LOG_FILE = "actual_expenses.json"

# Default baseline configurations
DEFAULT_BUDGET = {
    "your_salary": 34000.0,
    "your_net": 2220.0,
    "wife_hourly_rate": 12.71,
    "wife_hours_per_week": 12.0,
    "use_proportional_split": True,
    "custom_split_ratio": 75.0,
    "loans_paused": True,
}

DEFAULT_EXPENSES = [
    {
        "name": "Rent",
        "category": "Housing",
        "cost": 1425.0,
        "type": "Set Shared",
    },
    {
        "name": "Council Tax",
        "category": "Housing",
        "cost": 125.0,
        "type": "Set Shared",
    },
    {
        "name": "Energy",
        "category": "Utilities",
        "cost": 65.0,
        "type": "Set Shared",
    },
    {"name": "Water", "category": "Utilities", "cost": 55.0, "type": "Set Shared"},
    {
        "name": "Wifi",
        "category": "Entertainment",
        "cost": 30.0,
        "type": "Set Shared",
    },
    {
        "name": "Food for 2",
        "category": "Groceries",
        "cost": 400.0,
        "type": "Variable Shared",
    },
    {
        "name": "Bank Cost",
        "category": "Finance",
        "cost": 15.0,
        "type": "Set Individual (You)",
    },
    {
        "name": "Loans",
        "category": "Finance",
        "cost": 160.0,
        "type": "Set Individual (You)",
    },
]

DEFAULT_GOALS = [
    {
        "goal_name": "Emergency Fund",
        "target_amount": 5000.0,
        "current_saved": 1200.0,
    }
]


def load_json_data(file_path, default_structure):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                loaded = json.load(f)
                if isinstance(default_structure, dict):
                    return {**default_structure, **loaded}
                return loaded
        except Exception:
            return default_structure
    return default_structure


def save_json_data(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)


# Initialize application persistent states
if "budget" not in st.session_state:
    st.session_state.budget = load_json_data(DATA_FILE, DEFAULT_BUDGET)
if "expenses" not in st.session_state:
    st.session_state.expenses = load_json_data(EXPENSES_FILE, DEFAULT_EXPENSES)
if "savings_goals" not in st.session_state:
    st.session_state.savings_goals = load_json_data(SAVINGS_FILE, DEFAULT_GOALS)
if "history" not in st.session_state:
    st.session_state.history = load_json_data(HISTORY_FILE, [])
if "actual_logs" not in st.session_state:
    st.session_state.actual_logs = load_json_data(LOG_FILE, [])

st.set_page_config(layout="wide", page_title="Advanced Financial Dashboard")
st.title("📊 Advanced Budget & Financial Management Suite")

# Main Navigation Tabs
tab_dashboard, tab_categories, tab_goals, tab_tracker, tab_history = st.tabs(
    [
        "💵 Budget Dashboard",
        "📂 Category Breakdown",
        "🎯 Savings Goals",
        "🧾 Expense Tracker Log",
        "📅 Historical Logs",
    ]
)

# ==========================================
# SIDEBAR CONFIGURATION INTERFACE
# ==========================================
with st.sidebar:
    st.header("💼 Income & Core Controls")

    st.subheader("Your Posture")
    your_salary = st.number_input(
        "Your Gross Annual Salary (£)",
        value=float(st.session_state.budget["your_salary"]),
        step=500.0,
    )
    your_net = st.number_input(
        "Your Monthly Net Pay (£)",
        value=float(st.session_state.budget["your_net"]),
        step=50.0,
    )

    st.divider()
    st.subheader("Wife's Hourly Calculator")
    wife_hr = st.number_input(
        "Wife's Hourly Rate (£)",
        value=float(st.session_state.budget["wife_hourly_rate"]),
        step=0.10,
    )
    wife_hours = st.number_input(
        "Wife's Hours per Week",
        value=float(st.session_state.budget["wife_hours_per_week"]),
        step=1.0,
    )

    # Dynamic calculation
    partner_gross_annual = wife_hr * wife_hours * 52.0
    partner_net = partner_gross_annual / 12.0

    st.info(
        f"Wife's Monthly Income: **£{partner_net:.2f}**\n(Annual: £{partner_gross_annual:.2f})"
    )

    st.divider()
    st.subheader("⚖️ Expense Split Engine")
    split_method = st.radio(
        "Splitting Strategy",
        ["Proportional to Income", "Manual Custom Ratio"],
        index=0 if st.session_state.budget["use_proportional_split"] else 1,
    )
    use_prop = split_method == "Proportional to Income"

    custom_ratio = st.slider(
        "Your Responsibility Share (%)",
        min_value=0.0,
        max_value=100.0,
        value=float(st.session_state.budget["custom_split_ratio"]),
        step=1.0,
    )

    st.divider()
    loans_paused = st.checkbox(
        "Pause Loan Payments", value=st.session_state.budget["loans_paused"]
    )

# Compute dynamic splits
total_net = your_net + partner_net
if use_prop:
    your_share_pct = (your_net / total_net) if total_net > 0 else 1.0
    partner_share_pct = 1.0 - your_share_pct
else:
    your_share_pct = custom_ratio / 100.0
    partner_share_pct = 1.0 - your_share_pct

# Sync budget settings state
updated_budget = {
    "your_salary": your_salary,
    "your_net": your_net,
    "wife_hourly_rate": wife_hr,
    "wife_hours_per_week": wife_hours,
    "use_proportional_split": use_prop,
    "custom_split_ratio": custom_ratio,
    "loans_paused": loans_paused,
}

if updated_budget != st.session_state.budget:
    st.session_state.budget = updated_budget
    save_json_data(DATA_FILE, updated_budget)

# Shared Active Expense Engine logic
active_expenses = [
    exp
    for exp in st.session_state.expenses
    if not (exp["name"] == "Loans" and loans_paused)
]

# Shared outgoings calculation
your_outgoings = 0.0
partner_outgoings = 0.0
for exp in active_expenses:
    cost = exp["cost"]
    extype = exp["type"]
    if extype in ["Set Shared", "Variable Shared"]:
        your_outgoings += cost * your_share_pct
        partner_outgoings += cost * partner_share_pct
    elif extype == "Set Individual (You)":
        your_outgoings += cost
    elif extype == "Set Individual (Partner)":
        partner_outgoings += cost

your_savings = your_net - your_outgoings
partner_savings = partner_net - partner_outgoings

# ==========================================
# TAB 1: BUDGET DASHBOARD
# ==========================================
with tab_dashboard:
    st.header("🛠️ Expense Management Ledger")

    edited_expenses = st.data_editor(
        active_expenses,
        num_rows="dynamic",
        column_config={
            "name": st.column_config.TextColumn("Expense Name", required=True),
            "category": st.column_config.SelectboxColumn(
                "Category",
                options=[
                    "Housing",
                    "Utilities",
                    "Groceries",
                    "Entertainment",
                    "Finance",
                    "Transport",
                    "Other",
                ],
                required=True,
            ),
            "cost": st.column_config.NumberColumn(
                "Total Monthly Cost (£)",
                min_value=0.0,
                format="£%.2f",
                required=True,
            ),
            "type": st.column_config.SelectboxColumn(
                "Expense Type",
                options=[
                    "Set Shared",
                    "Variable Shared",
                    "Set Individual (You)",
                    "Set Individual (Partner)",
                ],
                required=True,
            ),
        },
        key="expense_editor",
    )

    if edited_expenses != active_expenses:
        new_master = list(edited_expenses)
        if loans_paused and not any(e["name"] == "Loans" for e in new_master):
            loan_entry = next(
                (e for e in st.session_state.expenses if e["name"] == "Loans"),
                {
                    "name": "Loans",
                    "category": "Finance",
                    "cost": 160.0,
                    "type": "Set Individual (You)",
                },
            )
            new_master.append(loan_entry)
        st.session_state.expenses = new_master
        save_json_data(EXPENSES_FILE, new_master)

    st.divider()
    st.header("📈 Allocation Visuals")
    st.write(
        f"**Split Ratio:** You **{your_share_pct*100:.1f}%** | Partner **{partner_share_pct*100:.1f}%**"
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Your Outgoings", f"£{your_outgoings:.2f}")
    m2.metric("Partner Outgoings", f"£{partner_outgoings:.2f}")
    if your_savings >= 0:
        m3.success(f"Your Surplus:\n**£{your_savings:.2f}**")
    else:
        m3.error(f"Your Deficit:\n**£{your_savings:.2f}**")
    if partner_savings >= 0:
        m4.success(f"Wife's Surplus:\n**£{partner_savings:.2f}**")
    else:
        m4.error(f"Wife's Deficit:\n**£{partner_savings:.2f}**")

    df_chart = pd.DataFrame(
        {
            "Individual": ["You", "You", "Wife", "Wife"],
            "Type": [
                "Allocated Outgoings",
                "Remaining Surplus",
                "Allocated Outgoings",
                "Remaining Surplus",
            ],
            "Amount (£)": [
                your_outgoings,
                max(0.0, your_savings),
                partner_outgoings,
                max(0.0, partner_savings),
            ],
        }
    )
    st.bar_chart(
        data=df_chart,
        x="Individual",
        y="Amount (£)",
        color="Type",
        stack=True,
        use_container_width=True,
    )

# ==========================================
# TAB 2: CATEGORY BREAKDOWN
# ==========================================
with tab_categories:
    st.header("📂 Category Breakdown & Distribution")
    df_exp = pd.DataFrame(active_expenses)

    if not df_exp.empty:
        cat_summary = (
            df_exp.groupby("category")["cost"].sum().reset_index()
        )
        cat_summary.columns = ["Category", "Total Cost (£)"]

        col_left, col_right = st.columns([1, 1])
        with col_left:
            st.subheader("Category Totals")
            st.dataframe(cat_summary, use_container_width=True)

        with col_right:
            st.subheader("Spending Distribution")
            # Native Streamlit bar breakdown chart by category
            st.bar_chart(
                data=cat_summary,
                x="Category",
                y="Total Cost (£)",
                use_container_width=True,
            )
    else:
        st.info("No active expenses found.")

# ==========================================
# TAB 3: SAVINGS GOALS TRACKER
# ==========================================
with tab_goals:
    st.header("🎯 Savings Goals Tracker")

    # Add Goal Form
    with st.expander("➕ Add New Savings Goal"):
        with st.form("new_goal_form"):
            g_name = st.text_input("Goal Name", placeholder="e.g. Holiday Fund")
            g_target = st.number_input(
                "Target Amount (£)", min_value=10.0, step=50.0
            )
            g_current = st.number_input(
                "Starting Saved Amount (£)", min_value=0.0, step=10.0
            )
            submitted = st.form_submit_button("Add Goal")
            if submitted and g_name:
                st.session_state.savings_goals.append(
                    {
                        "goal_name": g_name,
                        "target_amount": g_target,
                        "current_saved": g_current,
                    }
                )
                save_json_data(SAVINGS_FILE, st.session_state.savings_goals)
                st.rerun()

    # Render Active Goals
    if st.session_state.savings_goals:
        for idx, goal in enumerate(st.session_state.savings_goals):
            st.subheader(f"📌 {goal['goal_name']}")
            target = goal["target_amount"]
            saved = goal["current_saved"]
            pct = min(100.0, (saved / target) if target > 0 else 0.0)

            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.progress(pct / 100.0)
                st.write(
                    f"Saved: **£{saved:.2f}** / **£{target:.2f}** ({pct:.1f}%)"
                )
            with c2:
                add_val = st.number_input(
                    "Deposit (£)",
                    min_value=0.0,
                    step=10.0,
                    key=f"deposit_{idx}",
                )
                if st.button("Add", key=f"btn_{idx}"):
                    st.session_state.savings_goals[idx]["current_saved"] += add_val
                    save_json_data(SAVINGS_FILE, st.session_state.savings_goals)
                    st.rerun()
            with c3:
                if st.button("Delete Goal", key=f"del_{idx}"):
                    st.session_state.savings_goals.pop(idx)
                    save_json_data(SAVINGS_FILE, st.session_state.savings_goals)
                    st.rerun()
            st.divider()

# ==========================================
# TAB 4: EXPENSE TRACKER / TRANSACTION LOG
# ==========================================
with tab_tracker:
    st.header("🧾 Realized Expense & Transaction Tracker")
    st.write("Log actual payments made throughout the month.")

    with st.form("log_transaction_form"):
        col1, col2, col3, col4 = st.columns(4)
        t_date = col1.date_input("Date", value=datetime.today())
        t_item = col2.text_input("Item / Description")
        t_amount = col3.number_input("Amount (£)", min_value=0.01, step=5.0)
        t_paid_by = col4.selectbox("Paid By", ["You", "Partner", "Shared Account"])
        submit_log = st.form_submit_button("Log Payment")

        if submit_log and t_item:
            new_log = {
                "date": str(t_date),
                "item": t_item,
                "amount": t_amount,
                "paid_by": t_paid_by,
            }
            st.session_state.actual_logs.append(new_log)
            save_json_data(LOG_FILE, st.session_state.actual_logs)
            st.success("Transaction recorded successfully!")
            st.rerun()

    if st.session_state.actual_logs:
        st.subheader("Logged Transactions")
        df_logs = pd.DataFrame(st.session_state.actual_logs)
        st.dataframe(df_logs, use_container_width=True)

        if st.button("Clear Logged Transactions"):
            st.session_state.actual_logs = []
            save_json_data(LOG_FILE, [])
            st.rerun()

# ==========================================
# TAB 5: HISTORICAL LOGS
# ==========================================
with tab_history:
    st.header("📅 Historical Snapshot Logs")
    st.write("Save a snapshot of the current month to log long-term trends.")

    col_h1, col_h2 = st.columns([2, 1])
    with col_h1:
        month_label = st.text_input(
            "Snapshot Label",
            value=datetime.today().strftime("%B %Y"),
        )
    with col_h2:
        st.write(" ")
        st.write(" ")
        if st.button("📸 Save Current Month Snapshot"):
            snapshot = {
                "date": month_label,
                "your_net": your_net,
                "partner_net": partner_net,
                "your_outgoings": your_outgoings,
                "partner_outgoings": partner_outgoings,
                "your_savings": your_savings,
                "partner_savings": partner_savings,
            }
            st.session_state.history.append(snapshot)
            save_json_data(HISTORY_FILE, st.session_state.history)
            st.success(f"Snapshot saved for {month_label}!")

    if st.session_state.history:
        st.subheader("Historical Performance")
        df_hist = pd.DataFrame(st.session_state.history)
        st.dataframe(df_hist, use_container_width=True)

        # Plot Savings trend over time
        st.write("### Savings Trend Across Logged Months")
        st.line_chart(
            data=df_hist,
            x="date",
            y=["your_savings", "partner_savings"],
            use_container_width=True,
        )