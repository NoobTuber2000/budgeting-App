import streamlit as st
import json
import os

# Define local data persistence files
DATA_FILE = "budget_data.json"
EXPENSES_FILE = "expenses_data.json"

# Default baseline configurations
DEFAULT_BUDGET = {
    "your_salary": 34000.0,
    "your_net": 2220.0,
    "wife_hourly_rate": 12.71,
    "wife_hours_per_week": 12.0,
    "use_proportional_split": True,
    "custom_split_ratio": 75.0,  # Your percentage if manual override is used
    "loans_paused": True
}

DEFAULT_EXPENSES = [
    {"name": "Rent", "cost": 1425.0, "type": "Set Shared"},
    {"name": "Council Tax", "cost": 125.0, "type": "Set Shared"},
    {"name": "Energy", "cost": 65.0, "type": "Set Shared"},
    {"name": "Water", "cost": 55.0, "type": "Set Shared"},
    {"name": "Wifi", "cost": 30.0, "type": "Set Shared"},
    {"name": "Food for 2", "cost": 400.0, "type": "Variable Shared"},
    {"name": "Bank Cost", "cost": 15.0, "type": "Set Individual (You)"},
    {"name": "Loans", "cost": 160.0, "type": "Set Individual (You)"}
]

def load_json_data(file_path, default_structure):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                loaded = json.load(f)
                if isinstance(default_structure, dict):
                    return {**default_structure, **loaded}
                return loaded
        except:
            return default_structure
    return default_structure

def save_json_data(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

# Initialize application persistent state
if "budget" not in st.session_state:
    st.session_state.budget = load_json_data(DATA_FILE, DEFAULT_BUDGET)
if "expenses" not in st.session_state:
    st.session_state.expenses = load_json_data(EXPENSES_FILE, DEFAULT_EXPENSES)

st.set_page_config(layout="wide")
st.title("📊 Advanced Proportional Budget Dashboard")
st.write("Modify any parameters in the sidebar or tables below. Changes are saved instantly.")

# ==========================================
# SIDEBAR CONFIGURATION INTERFACE
# ==========================================
with st.sidebar:
    st.header("💼 Income & Core Controls")
    
    st.subheader("Your Posture")
    your_salary = st.number_input("Your Gross Annual Salary (£)", value=float(st.session_state.budget["your_salary"]), step=500.0)
    your_net = st.number_input("Your Monthly Net Pay (£)", value=float(st.session_state.budget["your_net"]), step=50.0)
    
    st.divider()
    st.subheader("Wife's Hourly Calculator")
    wife_hr = st.number_input("Wife's Hourly Rate (£)", value=float(st.session_state.budget["wife_hourly_rate"]), step=0.10)
    wife_hours = st.number_input("Wife's Hours per Week", value=float(st.session_state.budget["wife_hours_per_week"]), step=1.0)
    
    # Calculate partner's monthly net pay dynamically (Tax-free under threshold)
    partner_gross_annual = wife_hr * wife_hours * 52.0
    partner_net = partner_gross_annual / 12.0
    
    st.info(f"Wife's Calculated Monthly Income: **£{partner_net:.2f}**\n(Annual: £{partner_gross_annual:.2f})")
    
    st.divider()
    st.subheader("⚖️ Expense Split Engine")
    split_method = st.radio("Splitting Strategy", ["Proportional to Income", "Manual Custom Ratio"])
    use_prop = (split_method == "Proportional to Income")
    
    custom_ratio = st.slider("Your Responsibility Share (%)", min_value=0.0, max_value=100.0, value=float(st.session_state.budget["custom_split_ratio"]), step=1.0)
    
    st.divider()
    loans_paused = st.checkbox("Pause Loan Payments (Until November)", value=st.session_state.budget["loans_paused"])

# Recompute dynamic splits
total_gross = your_salary + partner_gross_annual
if use_prop:
    your_share_pct = (your_salary / total_gross) if total_gross > 0 else 1.0
    partner_share_pct = 1.0 - your_share_pct
else:
    your_share_pct = custom_ratio / 100.0
    partner_share_pct = 1.0 - your_share_pct

# Sync changes to session state and local data file
updated_budget = {
    "your_salary": your_salary, "your_net": your_net, "wife_hourly_rate": wife_hr,
    "wife_hours_per_week": wife_hours, "use_proportional_split": use_prop,
    "custom_split_ratio": custom_ratio, "loans_paused": loans_paused
}
if updated_budget != st.session_state.budget:
    st.session_state.budget = updated_budget
    save_json_data(DATA_FILE, updated_budget)
    st.rerun()

# ==========================================
# BUDGET MATRIX & EXPENSE MANAGEMENT ENGINE
# ==========================================
st.header("🛠️ Expense Management Ledger")
st.write("Edit item cells directly to modify costs, or utilize the interface below to append custom lines.")

# Clean/filter list based on loan state dynamically
active_expenses_list = []
for exp in st.session_state.expenses:
    if exp["name"] == "Loans" and loans_paused:
        continue
    active_expenses_list.append(exp)

# Render editable table grid framework
edited_expenses = st.data_editor(
    active_expenses_list,
    num_rows="dynamic",
    column_config={
        "name": st.column_config.TextColumn("Expense Name", required=True),
        "cost": st.column_config.NumberColumn("Total Monthly Cost (£)", min_value=0.0, format="£%.2f", required=True),
        "type": st.column_config.SelectboxColumn("Expense Type", options=["Set Shared", "Variable Shared", "Set Individual (You)", "Set Individual (Partner)"], required=True)
    },
    key="expense_editor"
)

# Re-sync ledger edits if structural adjustments occur inside the table
if st.session_state.expense_editor["edited_rows"] or st.session_state.expense_editor["added_rows"] or st.session_state.expense_editor["deleted_rows"]:
    # Rebuild full base master list including paused items if they were omitted visually
    new_master_list = list(edited_expenses)
    if loans_paused and not any(e["name"] == "Loans" for e in new_master_list):
        # Preserve loans entry if it was hidden under paused toggle state
        loan_entry = next((e for e in st.session_state.expenses if e["name"] == "Loans"), {"name": "Loans", "cost": 160.0, "type": "Set Individual (You)"})
        new_master_list.append(loan_entry)
    st.session_state.expenses = new_master_list
    save_json_data(EXPENSES_FILE, new_master_list)
    st.rerun()

# ==========================================
# FINANCIAL ENGINE CALCULATIONS & VISUALS
# ==========================================
your_total_outgoings = 0.0
partner_total_outgoings = 0.0

for exp in active_expenses_list:
    cost = exp["cost"]
    extype = exp["type"]
    
    if extype in ["Set Shared", "Variable Shared"]:
        your_total_outgoings += (cost * your_share_pct)
        partner_total_outgoings += (cost * partner_share_pct)
    elif extype == "Set Individual (You)":
        your_total_outgoings += cost
    elif extype == "Set Individual (Partner)":
        partner_total_outgoings += cost

your_savings = your_net - your_total_outgoings
partner_savings = partner_net - partner_total_outgoings

st.divider()
st.header("📈 Financial Performance Visuals")
st.subheader(f"Current Assignment Split: You **{your_share_pct*100:.1f}%** | Partner **{partner_share_pct*100:.1f}%**")

# Display Summary Metrics Row
m_col1, m_col2, m_col3, m_col4 = st.columns(4)
m_col1.metric("Your Responsibilities", f"£{your_total_outgoings:.2f}")
m_col2.metric("Partner Responsibilities", f"£{partner_total_outgoings:.2f}")

if your_savings >= 0:
    m_col3.success(f"Your Monthly Savings:\n**£{your_savings:.2f}**")
else:
    m_col3.error(f"Your Outgoings Deficit:\n**£{your_savings:.2f}**")

if partner_savings >= 0:
    m_col4.success(f"Wife's Monthly Savings:\n**£{partner_savings:.2f}**")
else:
    m_col4.error(f"Wife's Outgoings Deficit:\n**£{partner_savings:.2f}**")

# Chart Data Preparation
chart_data = {
    "Individual": ["You", "You", "Wife", "Wife"],
    "Type": ["Allocated Outgoings", "Remaining Surplus", "Allocated Outgoings", "Remaining Surplus"],
    "Amount (£)": [
        your_total_outgoings, 
        max(0.0, your_savings), 
        partner_total_outgoings, 
        max(0.0, partner_savings)
    ]
}

# Display full bar breakdown chart using native streamlit chart logic
st.write("### Cash Flow Allocations vs Monthly Capacity")
st.bar_chart(
    data=chart_data,
    x="Individual",
    y="Amount (£)",
    color="Type",
    stack=True,
    use_container_width=True
)