import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
import time
import math
import calendar
from datetime import datetime

DATA_FILE = "finance_data.json"

# --- Ορισμός Οικογενειών / Υποκατηγοριών ---
EXPENSE_CATEGORIES = {
    "Καθημερινά / Διαβίωση": [
        "Φαγητό", "Σούπερ Μάρκετ", "Φαρμακείο",
    ],
    "Μετακινήσεις / Όχημα": [
        "Βενζίνες", "Λεωφορείο", "Μετρό", "Ταξί", "Ενοικίαση Οχήματος", "Συντήρηση / Ανταλλακτικά" , "Διόδια" , "Αξεσουαρ"
    ],
    "Ψυχαγωγία / Προσωπικά": [
        "Ποτό", "Θέατρο / Σινεμά", "Κούρεμα", "Laser", "Διακοπές"
    ],
    "Εκπαίδευση": [
        "Ιταλικά", "Σεμινάρια / Μαθήματα", "Βιβλία"
    ],
    "Πάγια / Οικονομικά": [
        "Συνδρομές", "Λογαριασμός Τηλεφώνου", "Klarna", "Μεταφορά Χρημάτων σε τρίτους"
    ],
    "Αγορές / Δώρα": [
        "Αγορές Online", "Ρούχα / Παπούτσια", "Δώρα", "Ηλεκτρονικά"
    ],
    "Άλλα": [
        "Άλλες Δαπάνες"
    ]
}

GENERIC_OTHER = "Άλλες Δαπάνες"          # η γενική επιλογή της ομάδας "Άλλα"
OTHER_IN_GROUP = "Άλλο (περιέγραψε)"     # προσωπική κατηγορία μέσα σε οποιαδήποτε άλλη ομάδα
KNOWN_SUBCATEGORIES = sum(EXPENSE_CATEGORIES.values(), [])
NECESSITIES = ["Ανάγκη", "Θα μπορούσε μην είχε γίνει η δαπάνη αυτή", "Δεν έπρεπε να γίνει η δαπάνη αυτή"]

def infer_group(category):
    """Βρίσκει την Ομάδα από το όνομα της κατηγορίας (για παλιές εγγραφές χωρίς 'group')."""
    for p, subs in EXPENSE_CATEGORIES.items():
        if category in subs: return p
    return "Άλλα"

def subcategory_options(group):
    """Οι επιλογές 'Είδος Δαπάνης' μιας ομάδας, μαζί με επιλογή για δική σου περιγραφή."""
    subs = EXPENSE_CATEGORIES[group]
    return subs if GENERIC_OTHER in subs else subs + [OTHER_IN_GROUP]

def is_custom_choice(choice):
    return choice in (GENERIC_OTHER, OTHER_IN_GROUP)

GREEK_MONTHS = ["Ιανουάριος", "Φεβρουάριος", "Μάρτιος", "Απρίλιος", "Μάιος", "Ιούνιος",
                "Ιούλιος", "Αύγουστος", "Σεπτέμβριος", "Οκτώβριος", "Νοέμβριος", "Δεκέμβριος"]

def month_label(month_year):
    """'09/2026' -> 'Σεπτέμβριος 2026'"""
    m, y = month_year.split("/")
    return f"{GREEK_MONTHS[int(m) - 1]} {y}"

def expenses_df(expenses):
    """DataFrame δαπανών με έτοιμες στήλες ημερομηνίας, μήνα και ομάδας."""
    df = pd.DataFrame(expenses)
    df['parsed_date'] = pd.to_datetime(df['date'], format='%d/%m/%Y')
    df['month_year'] = df['parsed_date'].dt.strftime('%m/%Y')
    return df

st.set_page_config(page_title="Οργάνωση Εξόδων", page_icon="💶", layout="wide")

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "incomes" not in data:
                data["incomes"] = []
            # Παλιές εγγραφές χωρίς Ομάδα: συμπληρώνεται αυτόματα από την κατηγορία
            for exp in data["expenses"]:
                if exp.get("group") not in EXPENSE_CATEGORIES:
                    exp["group"] = infer_group(exp["category"])
            data.setdefault("budgets", {})
            return data
    else:
        return {"liquidity": {"Μετρητά": 0.0, "Revolut": 0.0, "Πειραιώς": 0.0}, "expenses": [], "incomes": [], "liquidity_updates": [], "budgets": {}}

def auto_budgets(expenses, today):
    """Αυτόματο budget ανά Ομάδα: μέσος όρος των ολοκληρωμένων μηνών, στρογγυλεμένος προς τα πάνω στα 10 €."""
    if not expenses: return {}
    df = expenses_df(expenses)
    month_start = pd.Timestamp(today.year, today.month, 1)
    past = df[df['parsed_date'] < month_start]
    if past.empty: return {}
    n_months = past['month_year'].nunique()
    per_group = past.groupby('group')['amount'].sum() / n_months
    return {g: float(math.ceil(v / 10) * 10) for g, v in per_group.items() if v > 0}

def effective_budgets(data, today):
    """{ομάδα: (ποσό, είναι_αυτόματο)} — τα αποθηκευμένα budget υπερισχύουν των αυτόματων."""
    saved = data.get("budgets", {})
    auto = auto_budgets(data["expenses"], today)
    result = {}
    for g in EXPENSE_CATEGORIES:
        if g in saved:
            if saved[g] > 0: result[g] = (float(saved[g]), False)   # 0 = χωρίς budget
        elif g in auto:
            result[g] = (auto[g], True)
    return result

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

data = load_data()

# --- Υπολογισμοί Μηνιαίας Σύγκρισης ---
now = datetime.now()
curr_month, curr_year = now.month, now.year
prev_month = 12 if curr_month == 1 else curr_month - 1
prev_year = curr_year - 1 if curr_month == 1 else curr_year

# Δίκαιη σύγκριση: ο τρέχων μήνας (1 έως σήμερα) συγκρίνεται με τις ίδιες ημέρες
# του προηγούμενου μήνα, όχι με ολόκληρο τον προηγούμενο μήνα.
same_period_label = f"1–{now.day}/{prev_month:02d}"

curr_month_exp = 0.0
prev_month_exp = 0.0           # ολόκληρος ο προηγ. μήνας
prev_month_exp_same = 0.0      # προηγ. μήνας, ημέρες 1..σήμερα
weekly_expenses = 0.0

for exp in data["expenses"]:
    try:
        exp_date = datetime.strptime(exp["date"], "%d/%m/%Y")
        if exp_date.month == curr_month and exp_date.year == curr_year:
            curr_month_exp += exp["amount"]
        elif exp_date.month == prev_month and exp_date.year == prev_year:
            prev_month_exp += exp["amount"]
            if exp_date.day <= now.day:
                prev_month_exp_same += exp["amount"]

        if 0 <= (now - exp_date).days <= 7:
            weekly_expenses += exp["amount"]
    except ValueError:
        pass

curr_month_inc = 0.0
prev_month_inc = 0.0
prev_month_inc_same = 0.0
for inc in data["incomes"]:
    try:
        inc_date = datetime.strptime(inc["date"], "%d/%m/%Y")
        if inc_date.month == curr_month and inc_date.year == curr_year:
            curr_month_inc += inc["amount"]
        elif inc_date.month == prev_month and inc_date.year == prev_year:
            prev_month_inc += inc["amount"]
            if inc_date.day <= now.day:
                prev_month_inc_same += inc["amount"]
    except ValueError:
        pass

total_liquidity = sum(data["liquidity"].values())
exp_delta = curr_month_exp - prev_month_exp_same
inc_delta = curr_month_inc - prev_month_inc_same

st.sidebar.title("Γεια σου, Γιάννη! 👋")
st.sidebar.write("Επίλεξε λειτουργία:")
menu = st.sidebar.radio("", ["🏠 Dashboard", "💰 Ενημέρωση Ρευστότητας", "⬇️ Καταγραφή Εσόδου", "🛒 Καταγραφή Δαπάνης", "✏️ Επεξεργασία Δαπάνης", "📊 Ιστορικό & Εξαγωγή", "📈 Σύγκριση Μηνών", "⚙️ Ρυθμίσεις", "🚪 Έξοδος"])

# ==========================================
# 1. DASHBOARD
# ==========================================
if menu == "🏠 Dashboard":
    st.title("Συνοπτική Εικόνα Οικονομικών")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Συνολικό Ρευστό", f"{total_liquidity:.2f} €")
    col2.metric("Έσοδα Τρέχοντος Μήνα", f"{curr_month_inc:.2f} €", f"{inc_delta:+.2f} € vs {same_period_label}",
                help=f"Σύγκριση με τις ίδιες ημέρες ({same_period_label}) του προηγ. μήνα: {prev_month_inc_same:.2f} €. "
                     f"Ολόκληρος ο προηγ. μήνας: {prev_month_inc:.2f} €.")
    col3.metric("Έξοδα Τρέχοντος Μήνα", f"{curr_month_exp:.2f} €", f"{exp_delta:+.2f} € vs {same_period_label}", delta_color="inverse",
                help=f"Σύγκριση με τις ίδιες ημέρες ({same_period_label}) του προηγ. μήνα: {prev_month_exp_same:.2f} €. "
                     f"Ολόκληρος ο προηγ. μήνας: {prev_month_exp:.2f} €.")
    col4.metric("Έξοδα (7 Ημερών)", f"{weekly_expenses:.2f} €")
    
    st.divider()

    # --- Budget Μήνα ανά Ομάδα ---
    budgets = effective_budgets(data, now)
    if budgets:
        days_in_month = calendar.monthrange(curr_year, curr_month)[1]
        spent_by_group = {}
        for exp in data["expenses"]:
            try:
                ed = datetime.strptime(exp["date"], "%d/%m/%Y")
            except ValueError:
                continue
            if ed.month == curr_month and ed.year == curr_year:
                spent_by_group[exp["group"]] = spent_by_group.get(exp["group"], 0.0) + exp["amount"]

        def projection(spent):
            return spent / now.day * days_in_month

        total_budget = sum(b for b, _ in budgets.values())
        total_spent_b = sum(spent_by_group.get(g, 0.0) for g in budgets)
        total_proj = projection(total_spent_b)

        st.subheader(f"💼 Budget {GREEK_MONTHS[curr_month - 1]}")
        st.caption(f"Ημέρα {now.day} από {days_in_month}. Η πρόβλεψη υποθέτει ότι συνεχίζεις με τον ίδιο ρυθμό μέχρι το τέλος του μήνα. "
                   "Όσα έχουν την ένδειξη (αυτόματο) είναι ο μέσος όρος των προηγούμενων μηνών· άλλαξέ τα από τις ⚙️ Ρυθμίσεις.")
        b1, b2, b3 = st.columns(3)
        b1.metric("Budget μήνα", f"{total_budget:.2f} €")
        b2.metric("Ξοδεύτηκαν", f"{total_spent_b:.2f} €", f"υπόλοιπο {total_budget - total_spent_b:.2f} €", delta_color="off")
        b3.metric("Πρόβλεψη τέλους μήνα", f"{total_proj:.2f} €", f"{total_proj - total_budget:+.2f} € vs budget", delta_color="inverse")

        bc1, bc2 = st.columns(2)
        for i, (g, (budget, is_auto)) in enumerate(budgets.items()):
            spent = spent_by_group.get(g, 0.0)
            proj = projection(spent)
            if spent > budget:   status = "🔴"
            elif proj > budget:  status = "🟠"
            else:                status = "🟢"
            auto_txt = " (αυτόματο)" if is_auto else ""
            ratio = min(spent / budget, 1.0) if budget > 0 else 1.0
            with (bc1 if i % 2 == 0 else bc2):
                st.progress(ratio, text=f"{status} **{g}**{auto_txt}: {spent:.0f} / {budget:.0f} € · πρόβλεψη {proj:.0f} €")

        no_budget = [g for g in spent_by_group if g not in budgets]
        if no_budget:
            st.caption("Χωρίς budget: " + ", ".join(f"{g} ({spent_by_group[g]:.0f} €)" for g in no_budget))
        st.caption("🟢 εντός budget · 🟠 με αυτόν τον ρυθμό θα το ξεπεράσεις · 🔴 το ξεπέρασες ήδη")
        st.divider()

    # --- Περιττά Έξοδα ---
    if data["expenses"]:
        df_dash = expenses_df(data["expenses"])
        d = df_dash['parsed_date']
        in_curr = (d.dt.month == curr_month) & (d.dt.year == curr_year)
        in_prev_same = (d.dt.month == prev_month) & (d.dt.year == prev_year) & (d.dt.day <= now.day)
        avoidable = df_dash['necessity'].isin(NECESSITIES[1:])

        av_curr = df_dash.loc[in_curr & avoidable, 'amount'].sum()
        av_prev_same = df_dash.loc[in_prev_same & avoidable, 'amount'].sum()
        could = df_dash.loc[in_curr & (df_dash['necessity'] == NECESSITIES[1]), 'amount'].sum()
        shouldnt = df_dash.loc[in_curr & (df_dash['necessity'] == NECESSITIES[2]), 'amount'].sum()
        av_pct = av_curr / curr_month_exp * 100 if curr_month_exp else 0.0
        monthly_avg_av = df_dash.loc[avoidable].groupby('month_year')['amount'].sum().reindex(
            df_dash['month_year'].unique(), fill_value=0).mean()

        st.subheader("🎯 Περιττά Έξοδα Μήνα")
        st.caption("Δαπάνες που σημείωσες ως «Θα μπορούσε να μην είχε γίνει» ή «Δεν έπρεπε να γίνει»: "
                   "τα χρήματα που θα μπορούσες να είχες γλιτώσει.")
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Περιττά αυτόν τον μήνα", f"{av_curr:.2f} €", f"{av_curr - av_prev_same:+.2f} € vs {same_period_label}",
                  delta_color="inverse")
        a2.metric("% των εξόδων του μήνα", f"{av_pct:.1f} %")
        a3.metric("Θα μπορούσαν να μην γίνουν", f"{could:.2f} €")
        a4.metric("Δεν έπρεπε να γίνουν", f"{shouldnt:.2f} €")
        if monthly_avg_av > 0:
            st.caption(f"💡 Κατά μέσο όρο ξοδεύεις **{monthly_avg_av:.2f} €/μήνα** σε περιττά, "
                       f"δηλαδή περίπου **{monthly_avg_av * 12:.0f} € τον χρόνο**.")

        df_av_curr = df_dash[in_curr & avoidable]
        if not df_av_curr.empty:
            with st.expander("Ποια ήταν τα περιττά αυτού του μήνα"):
                av_table = df_av_curr.sort_values('amount', ascending=False)[['date', 'category', 'amount', 'necessity']]
                av_table.columns = ["Ημερ/νία", "Κατηγορία", "Ποσό (€)", "Σοβαρότητα"]
                st.dataframe(av_table, hide_index=True, use_container_width=True)
        st.divider()

    c_liq, c_top3 = st.columns(2)
    with c_liq:
        st.subheader("Ανάλυση Ρευστότητας")
        c1, c2, c3 = st.columns(3)
        c1.metric("Μετρητά", f"{data['liquidity']['Μετρητά']:.2f} €")
        c2.metric("Revolut", f"{data['liquidity']['Revolut']:.2f} €")
        c3.metric("Τράπεζα Πειραιώς", f"{data['liquidity']['Πειραιώς']:.2f} €")

    with c_top3:
        st.subheader("🏆 Top 3 Δαπάνες (Τρέχων Μήνας)")
        if data["expenses"]:
            df_curr = pd.DataFrame(data["expenses"])
            df_curr['parsed_date'] = pd.to_datetime(df_curr['date'], format='%d/%m/%Y')
            df_curr = df_curr[(df_curr['parsed_date'].dt.month == curr_month) & (df_curr['parsed_date'].dt.year == curr_year)]
            
            if not df_curr.empty:
                top3 = df_curr.nlargest(3, 'amount')[['date', 'category', 'amount']]
                top3.columns = ["Ημερ/νία", "Κατηγορία", "Ποσό (€)"]
                st.dataframe(top3, hide_index=True, use_container_width=True)
            else:
                st.info("Δεν υπάρχουν δαπάνες αυτόν τον μήνα.")
        else:
            st.info("Δεν υπάρχουν δαπάνες καταχωρημένες.")

    if data["expenses"]:
        st.divider()
        df_exp = expenses_df(data["expenses"])
        df_exp['parent_category'] = df_exp['group']
        
        df_exp = df_exp.sort_values('parsed_date')
        
        c_chart1, c_chart2 = st.columns(2)
        with c_chart1:
            st.subheader("Έξοδα ανά Ομάδα & Μήνα")
            category_sum = df_exp.groupby(["parent_category", "month_year"])["amount"].sum().reset_index()
            fig_cat = px.bar(
                category_sum, x="parent_category", y="amount", color="month_year", 
                barmode="group", labels={"parent_category": "Ομάδα Δαπανών", "amount": "Ποσό (€)", "month_year": "Μήνας"}
            )
            st.plotly_chart(fig_cat, use_container_width=True)
            
        with c_chart2:
            st.subheader("Σοβαρότητα Εξόδων ανά Μήνα")
            necessity_sum = df_exp.groupby(["month_year", "necessity"])["amount"].sum().reset_index()
            fig_nec = px.bar(
                necessity_sum, x="month_year", y="amount", color="necessity",
                category_orders={"necessity": NECESSITIES},
                labels={"month_year": "Μήνας", "amount": "Ποσό (€)", "necessity": "Σοβαρότητα"}
            )
            st.plotly_chart(fig_nec, use_container_width=True)

        st.divider()
        st.subheader("Πορεία Εξόδων (ανά ημέρα)")
        real_date_sum = df_exp.groupby("parsed_date")["amount"].sum().reset_index()
        st.line_chart(real_date_sum.set_index("parsed_date"))

# ==========================================
# 2. ΕΝΗΜΕΡΩΣΗ ΡΕΥΣΤΟΤΗΤΑΣ
# ==========================================
elif menu == "💰 Ενημέρωση Ρευστότητας":
    st.title("Ενημέρωση Ρευστότητας")
    with st.form("liquidity_form"):
        date_input = st.date_input("Ημερομηνία", format="DD/MM/YYYY")
        col1, col2, col3 = st.columns(3)
        with col1:
            cash = st.number_input("Νέο υπόλοιπο σε Μετρητά (€)", min_value=0.0, value=float(data['liquidity']['Μετρητά']), format="%.2f")
            cash_comment = st.text_input("Σχόλιο προέλευσης μετρητών (προαιρετικό)")
        with col2:
            revolut = st.number_input("Νέο υπόλοιπο σε Revolut (€)", min_value=0.0, value=float(data['liquidity']['Revolut']), format="%.2f")
        with col3:
            piraeus = st.number_input("Νέο υπόλοιπο σε Πειραιώς (€)", min_value=0.0, value=float(data['liquidity']['Πειραιώς']), format="%.2f")
        if st.form_submit_button("Αποθήκευση Ρευστότητας"):
            data["liquidity"]["Μετρητά"], data["liquidity"]["Revolut"], data["liquidity"]["Πειραιώς"] = cash, revolut, piraeus
            data["liquidity_updates"].append({
                "date": date_input.strftime("%d/%m/%Y"), "cash": cash, "cash_comment": cash_comment,
                "revolut": revolut, "piraeus": piraeus
            })
            save_data(data)
            st.success("✅ Η ρευστότητα ενημερώθηκε επιτυχώς!")
            time.sleep(1.5)
            st.rerun()

# ==========================================
# 3. ΚΑΤΑΓΡΑΦΗ ΕΣΟΔΟΥ
# ==========================================
elif menu == "⬇️ Καταγραφή Εσόδου":
    st.title("Καταγραφή Νέου Εσόδου")
    with st.form("income_form"):
        date_input = st.date_input("Ημερομηνία", format="DD/MM/YYYY")
        source = st.text_input("Πηγή Εσόδου (π.χ. Μισθός, Επιστροφή, Δώρο)")
        amount = st.number_input("Ποσό Εσόδου (€)", min_value=0.01, step=10.0, format="%.2f")
        target_account = st.selectbox("Πού μπήκαν τα χρήματα;", ["Μετρητά", "Revolut", "Πειραιώς"])
        if st.form_submit_button("Καταχώρηση Εσόδου"):
            if not source.strip():
                st.error("❌ Παρακαλώ συμπλήρωσε την πηγή του εσόδου.")
            else:
                data["liquidity"][target_account] += amount
                data["incomes"].append({
                    "date": date_input.strftime("%d/%m/%Y"), "source": source,
                    "amount": amount, "account": target_account
                })
                save_data(data)
                st.success(f"✅ Το έσοδο {amount}€ καταγράφηκε! Το υπόλοιπο ({target_account}) αυξήθηκε αυτόματα.")
                time.sleep(1.5)
                st.rerun()

# ==========================================
# 4. ΚΑΤΑΓΡΑΦΗ ΔΑΠΑΝΗΣ
# ==========================================
elif menu == "🛒 Καταγραφή Δαπάνης":
    st.title("Καταγραφή Νέας Δαπάνης")
    date_input = st.date_input("Ημερομηνία", format="DD/MM/YYYY")
    
    col_p, col_s = st.columns(2)
    with col_p:
        parent_cat = st.selectbox("Ομάδα Δαπανών", list(EXPENSE_CATEGORIES.keys()))
    with col_s:
        category = st.selectbox("Είδος Δαπάνης", subcategory_options(parent_cat))

    other_category = st.text_input("Περιέγραψε την δαπάνη (π.χ. Δώρο γενεθλίων):") if is_custom_choice(category) else ""
    
    location = st.text_input("Τοποθεσία (π.χ. Αθήνα)")
    amount = st.number_input("Ποσό Δαπάνης (€)", min_value=0.01, step=0.5, format="%.2f")
    pay_method = st.selectbox("Τρόπος Πληρωμής", ["Μετρητά", "Revolut", "Τράπεζα Πειραιώς", "Άλλος τρόπος"])
    other_pay_method = st.text_input("Περιέγραψε τον τρόπο πληρωμής:") if pay_method == "Άλλος τρόπος" else ""
    necessity = st.selectbox("Πόσο σοβαρή ήταν η δαπάνη;", NECESSITIES)

    if st.button("Καταχώρηση Δαπάνης"):
        final_category = other_category.strip() if is_custom_choice(category) else category
        if not final_category:
            st.error("❌ Παρακαλώ περιέγραψε την δαπάνη.")
            st.stop()
        final_pay_method = other_pay_method if pay_method == "Άλλος τρόπος" else pay_method
        mapped_method = "Πειραιώς" if final_pay_method == "Τράπεζα Πειραιώς" else final_pay_method
        if mapped_method in data["liquidity"]: data["liquidity"][mapped_method] -= amount
        data["expenses"].append({
            "date": date_input.strftime("%d/%m/%Y"), "group": parent_cat, "category": final_category,
            "location": location, "amount": amount, "payment_method": final_pay_method, "necessity": necessity
        })
        save_data(data)
        st.success(f"✅ Η δαπάνη {amount}€ καταγράφηκε! Αφαιρέθηκε αυτόματα από: {final_pay_method}")
        time.sleep(1.5)
        st.rerun()

# ==========================================
# 5. ΕΠΕΞΕΡΓΑΣΙΑ / ΔΙΑΓΡΑΦΗ ΔΑΠΑΝΗΣ
# ==========================================
elif menu == "✏️ Επεξεργασία Δαπάνης":
    st.title("Επεξεργασία ή Διαγραφή Δαπάνης")
    if not data["expenses"]:
        st.info("Δεν υπάρχουν καταχωρημένες δαπάνες για επεξεργασία.")
    else:
        df_edit = pd.DataFrame(data["expenses"])
        df_edit['original_index'] = df_edit.index
        df_edit['parsed_date'] = pd.to_datetime(df_edit['date'], format='%d/%m/%Y')
        df_edit['month_year'] = df_edit['parsed_date'].dt.strftime('%m/%Y')
        df_edit = df_edit.sort_values('parsed_date', ascending=False)
        
        months_available = list(df_edit['month_year'].unique())
        selected_month = st.selectbox("📅 Φιλτράρισμα ανά Μήνα:", ["Όλοι"] + months_available)
        
        if selected_month != "Όλοι":
            df_filtered = df_edit[df_edit['month_year'] == selected_month]
        else:
            df_filtered = df_edit
            
        if df_filtered.empty:
            st.warning("Δεν βρέθηκαν δαπάνες για τα κριτήρια αυτά.")
        else:
            expense_options = [f"{row['original_index']}: {row['date']} | {row['category']} | {row['amount']}€ ({row['payment_method']})" for _, row in df_filtered.iterrows()]
            selected_option = st.selectbox("Επίλεξε ποια δαπάνη θέλεις να επεξεργαστείς:", expense_options)
            
            selected_idx = int(selected_option.split(":")[0])
            exp_to_edit = data["expenses"][selected_idx]
            
            st.divider()
            new_date = st.date_input("Ημερομηνία", datetime.strptime(exp_to_edit["date"], "%d/%m/%Y"), format="DD/MM/YYYY")
            
            # Ομάδα: αποθηκευμένη στην εγγραφή (ή συμπληρωμένη αυτόματα στη φόρτωση)
            p_val = exp_to_edit.get("group", infer_group(exp_to_edit["category"]))
            cur_is_custom = exp_to_edit["category"] not in KNOWN_SUBCATEGORIES

            col_p, col_s = st.columns(2)
            with col_p:
                p_idx = list(EXPENSE_CATEGORIES.keys()).index(p_val)
                new_parent_cat = st.selectbox("Ομάδα Δαπανών", list(EXPENSE_CATEGORIES.keys()), index=p_idx)
            with col_s:
                sub_opts = subcategory_options(new_parent_cat)
                if exp_to_edit["category"] in sub_opts:
                    s_idx = sub_opts.index(exp_to_edit["category"])
                elif cur_is_custom:
                    s_idx = len(sub_opts) - 1   # η επιλογή "Άλλο" είναι πάντα τελευταία
                else:
                    s_idx = 0
                new_category = st.selectbox("Είδος Δαπάνης", sub_opts, index=s_idx)

            new_other_category = ""
            if is_custom_choice(new_category):
                default_custom = exp_to_edit["category"] if cur_is_custom else ""
                new_other_category = st.text_input("Περιέγραψε την δαπάνη:", value=default_custom)
                
            new_location = st.text_input("Τοποθεσία", value=exp_to_edit["location"])
            new_amount = st.number_input("Ποσό Δαπάνης (€)", min_value=0.01, step=0.5, value=float(exp_to_edit["amount"]), format="%.2f")
            
            pay_methods = ["Μετρητά", "Revolut", "Τράπεζα Πειραιώς", "Άλλος τρόπος"]
            pm_idx = pay_methods.index(exp_to_edit["payment_method"]) if exp_to_edit["payment_method"] in pay_methods else 3
            new_pay_method = st.selectbox("Τρόπος Πληρωμής", pay_methods, index=pm_idx)
            new_other_pay_method = st.text_input("Περιέγραψε τον τρόπο πληρωμής:", value=exp_to_edit["payment_method"] if pm_idx == 3 else "") if new_pay_method == "Άλλος τρόπος" else ""
            nec_idx = NECESSITIES.index(exp_to_edit["necessity"]) if exp_to_edit["necessity"] in NECESSITIES else 0
            new_necessity = st.selectbox("Πόσο σοβαρή ήταν η δαπάνη;", NECESSITIES, index=nec_idx)

            col1, col2 = st.columns(2)
            if col1.button("💾 Αποθήκευση Αλλαγών"):
                final_category = new_other_category.strip() if is_custom_choice(new_category) else new_category
                if not final_category:
                    st.error("❌ Παρακαλώ περιέγραψε την δαπάνη.")
                    st.stop()
                final_pay_method = new_other_pay_method if new_pay_method == "Άλλος τρόπος" else new_pay_method
                old_pay_method, old_amount = exp_to_edit["payment_method"], exp_to_edit["amount"]
                mapped_old_pm = "Πειραιώς" if old_pay_method == "Τράπεζα Πειραιώς" else old_pay_method
                if mapped_old_pm in data["liquidity"]: data["liquidity"][mapped_old_pm] += old_amount
                mapped_new_pm = "Πειραιώς" if final_pay_method == "Τράπεζα Πειραιώς" else final_pay_method
                if mapped_new_pm in data["liquidity"]: data["liquidity"][mapped_new_pm] -= new_amount
                data["expenses"][selected_idx] = {
                    "date": new_date.strftime("%d/%m/%Y"), "group": new_parent_cat, "category": final_category, "location": new_location,
                    "amount": new_amount, "payment_method": final_pay_method, "necessity": new_necessity
                }
                save_data(data)
                st.success("✅ Η δαπάνη ενημερώθηκε και η ρευστότητα προσαρμόστηκε αυτόματα!")
                time.sleep(1.5)
                st.rerun()
                
            elif col2.button("🗑️ Οριστική Διαγραφή"):
                old_pay_method, old_amount = exp_to_edit["payment_method"], exp_to_edit["amount"]
                mapped_old_pm = "Πειραιώς" if old_pay_method == "Τράπεζα Πειραιώς" else old_pay_method
                if mapped_old_pm in data["liquidity"]: data["liquidity"][mapped_old_pm] += old_amount
                data["expenses"].pop(selected_idx)
                save_data(data)
                st.success("🗑️ Η δαπάνη διαγράφηκε και το ποσό επιστράφηκε στο ταμείο σου!")
                time.sleep(1.5)
                st.rerun()

# ==========================================
# 6. ΙΣΤΟΡΙΚΟ & ΕΞΑΓΩΓΗ
# ==========================================
elif menu == "📊 Ιστορικό & Εξαγωγή":
    st.title("Ιστορικό Εξόδων")
    if not data["expenses"]:
        st.info("Δεν υπάρχουν καταχωρημένα έξοδα ακόμα.")
    else:
        df = expenses_df(data["expenses"])
        df['parent_category'] = df['group']

        st.subheader("Φίλτρα Αναζήτησης")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            # Μήνες ταξινομημένοι από τον πιο πρόσφατο
            months_sorted = df.sort_values('parsed_date', ascending=False)['month_year'].unique()
            months = ["Όλοι"] + list(months_sorted)
            selected_month = st.selectbox("Μήνας", months)
        with col2:
            groups = ["Όλες"] + [g for g in EXPENSE_CATEGORIES.keys() if g in df['parent_category'].values]
            selected_group = st.selectbox("Ομάδα", groups)
        with col3:
            cat_source = df if selected_group == "Όλες" else df[df['parent_category'] == selected_group]
            categories = ["Όλες"] + sorted(cat_source['category'].unique())
            selected_category = st.selectbox("Κατηγορία", categories)
        with col4:
            pay_methods = ["Όλοι"] + list(df['payment_method'].unique())
            selected_pay_method = st.selectbox("Τρόπος Πληρωμής", pay_methods)

        filtered_df = df.copy()
        if selected_month != "Όλοι": filtered_df = filtered_df[filtered_df['month_year'] == selected_month]
        if selected_group != "Όλες": filtered_df = filtered_df[filtered_df['parent_category'] == selected_group]
        if selected_category != "Όλες": filtered_df = filtered_df[filtered_df['category'] == selected_category]
        if selected_pay_method != "Όλοι": filtered_df = filtered_df[filtered_df['payment_method'] == selected_pay_method]
        filtered_df = filtered_df.sort_values('parsed_date')

        st.divider()
        st.write(f"Εμφάνιση **{len(filtered_df)}** αποτελεσμάτων:")
        display_df = filtered_df[['date', 'category', 'location', 'amount', 'payment_method', 'necessity']].copy()
        display_df.columns = ["Ημερομηνία", "Κατηγορία", "Τοποθεσία", "Ποσό (€)", "Τρόπος Πληρωμής", "Σοβαρότητα"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # --- Σύνολο φιλτραρισμένων ---
        total_filtered = filtered_df['amount'].sum()
        count_filtered = len(filtered_df)
        avg_filtered = total_filtered / count_filtered if count_filtered else 0.0

        filter_parts = []
        if selected_month != "Όλοι": filter_parts.append(f"Μήνας {selected_month}")
        if selected_group != "Όλες": filter_parts.append(selected_group)
        if selected_category != "Όλες": filter_parts.append(selected_category)
        if selected_pay_method != "Όλοι": filter_parts.append(selected_pay_method)
        filter_label = " · ".join(filter_parts) if filter_parts else "Όλες οι δαπάνες"

        st.subheader(f"💶 Σύνολο: {filter_label}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Συνολικό Ποσό", f"{total_filtered:.2f} €")
        m2.metric("Πλήθος Δαπανών", f"{count_filtered}")
        m3.metric("Μέσος Όρος / Δαπάνη", f"{avg_filtered:.2f} €")

        if count_filtered and selected_category == "Όλες":
            with st.expander("Ανάλυση συνόλου ανά κατηγορία"):
                breakdown = filtered_df.groupby('category')['amount'].agg(['sum', 'count']).reset_index()
                breakdown = breakdown.sort_values('sum', ascending=False)
                breakdown['pct'] = (breakdown['sum'] / total_filtered * 100).round(1)
                breakdown.columns = ["Κατηγορία", "Ποσό (€)", "Πλήθος", "% του συνόλου"]
                st.dataframe(breakdown, use_container_width=True, hide_index=True)

        # Εξαγωγή με γραμμή συνόλου στο τέλος
        export_df = pd.concat([
            display_df,
            pd.DataFrame([{"Ημερομηνία": "ΣΥΝΟΛΟ", "Κατηγορία": filter_label, "Τοποθεσία": "",
                           "Ποσό (€)": round(total_filtered, 2), "Τρόπος Πληρωμής": "", "Σοβαρότητα": ""}])
        ], ignore_index=True)
        csv = export_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(label="📥 Λήψη Φιλτραρισμένων σε Excel (.csv)", data=csv, file_name='expenses_filtered.csv', mime='text/csv')

# ==========================================
# 6β. ΣΥΓΚΡΙΣΗ ΜΗΝΩΝ
# ==========================================
elif menu == "📈 Σύγκριση Μηνών":
    st.title("Σύγκριση Μηνών")
    if not data["expenses"]:
        st.info("Δεν υπάρχουν καταχωρημένα έξοδα ακόμα.")
    else:
        df = expenses_df(data["expenses"])
        months_sorted = list(df.sort_values('parsed_date', ascending=False)['month_year'].unique())

        if len(months_sorted) < 2:
            st.info("Χρειάζονται δαπάνες σε τουλάχιστον 2 μήνες για να γίνει σύγκριση.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            month_a = c1.selectbox("Μήνας Α (βάση)", months_sorted, index=1, format_func=month_label)
            month_b = c2.selectbox("Μήνας Β (σύγκριση)", months_sorted, index=0, format_func=month_label)
            level = c3.radio("Ανάλυση ανά", ["Ομάδα", "Κατηγορία"], horizontal=True)
            group_filter = "Όλες"
            if level == "Κατηγορία":
                group_filter = c4.selectbox("Ομάδα", ["Όλες"] + list(EXPENSE_CATEGORIES.keys()))

            if month_a == month_b:
                st.warning("Διάλεξε δύο διαφορετικούς μήνες.")
                st.stop()

            df_a = df[df['month_year'] == month_a]
            df_b = df[df['month_year'] == month_b]

            # Δίκαιη σύγκριση όταν ο ένας μήνας είναι ο τρέχων (δεν έχει τελειώσει)
            if now.strftime('%m/%Y') in (month_a, month_b):
                same_days = st.checkbox(
                    f"⚖️ Δίκαιη σύγκριση: μόνο ημέρες 1–{now.day} και στους δύο μήνες", value=True,
                    help="Ο τρέχων μήνας δεν έχει τελειώσει. Με αυτή την επιλογή συγκρίνεται με τις ίδιες ημέρες του άλλου μήνα.")
                if same_days:
                    df_a = df_a[df_a['parsed_date'].dt.day <= now.day]
                    df_b = df_b[df_b['parsed_date'].dt.day <= now.day]

            if group_filter != "Όλες":
                df_a = df_a[df_a['group'] == group_filter]
                df_b = df_b[df_b['group'] == group_filter]

            label_a, label_b = month_label(month_a), month_label(month_b)
            key = 'group' if level == "Ομάδα" else 'category'
            comp = pd.DataFrame({
                "A": df_a.groupby(key)['amount'].sum(),
                "B": df_b.groupby(key)['amount'].sum(),
            }).fillna(0.0)
            comp["diff"] = comp["B"] - comp["A"]
            comp = comp.sort_values("diff", ascending=False)

            # --- Σύνολα ---
            total_a, total_b = comp["A"].sum(), comp["B"].sum()
            total_diff = total_b - total_a
            total_pct = f" ({total_diff / total_a * 100:+.0f}%)" if total_a else ""
            st.divider()
            m1, m2, m3 = st.columns(3)
            m1.metric(f"Σύνολο {label_a}", f"{total_a:.2f} €")
            m2.metric(f"Σύνολο {label_b}", f"{total_b:.2f} €", f"{total_diff:+.2f} €{total_pct}", delta_color="inverse")
            m3.metric("Πλήθος Δαπανών (Α → Β)", f"{len(df_a)} → {len(df_b)}")

            # --- Τι άλλαξε περισσότερο ---
            ups = comp[comp["diff"] > 0]
            downs = comp[comp["diff"] < 0].sort_values("diff")
            i1, i2 = st.columns(2)
            with i1:
                if not ups.empty:
                    st.error("🔺 **Μεγαλύτερες αυξήσεις:**  \n" + "  \n".join(
                        f"{name}: +{row['diff']:.2f} €" for name, row in ups.head(3).iterrows()))
                else:
                    st.success("Καμία αύξηση! 🎉")
            with i2:
                if not downs.empty:
                    st.success("🔻 **Μεγαλύτερες μειώσεις:**  \n" + "  \n".join(
                        f"{name}: {row['diff']:.2f} €" for name, row in downs.head(3).iterrows()))
                else:
                    st.info("Καμία μείωση.")

            # --- Πίνακας ---
            def pct_text(row):
                if row["A"] == 0: return "νέο" if row["B"] > 0 else "—"
                return f"{row['diff'] / row['A'] * 100:+.0f}%"
            def trend(d):
                return "🔺" if d > 0.005 else ("🔻" if d < -0.005 else "➖")
            table = pd.DataFrame({
                level: comp.index,
                f"{label_a} (€)": comp["A"].round(2).values,
                f"{label_b} (€)": comp["B"].round(2).values,
                "Διαφορά (€)": comp["diff"].round(2).values,
                "Μεταβολή": comp.apply(pct_text, axis=1).values,
                "": comp["diff"].apply(trend).values,
            })
            st.subheader(f"Ανάλυση ανά {level}")
            st.dataframe(table, use_container_width=True, hide_index=True)

            # --- Γράφημα ---
            chart_df = pd.concat([
                pd.DataFrame({level: comp.index, "Ποσό (€)": comp["A"].values, "Μήνας": label_a}),
                pd.DataFrame({level: comp.index, "Ποσό (€)": comp["B"].values, "Μήνας": label_b}),
            ])
            fig = px.bar(chart_df, x=level, y="Ποσό (€)", color="Μήνας", barmode="group")
            st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 7. ΡΥΘΜΙΣΕΙΣ / ΜΗΔΕΝΙΣΜΟΣ
# ==========================================
elif menu == "⚙️ Ρυθμίσεις":
    st.title("Ρυθμίσεις Δεδομένων")

    # --- Αντιστοίχιση προσωπικών κατηγοριών σε Ομάδα ---
    st.subheader("🗂️ Προσωπικές Κατηγορίες → Ομάδα")
    custom_cats = sorted({e["category"] for e in data["expenses"] if e["category"] not in KNOWN_SUBCATEGORIES})
    if not custom_cats:
        st.info("Δεν υπάρχουν προσωπικές κατηγορίες.")
    else:
        st.caption("Δαπάνες που καταχώρησες με δική σου περιγραφή. Διάλεξε σε ποια Ομάδα ανήκει η καθεμία, "
                   "ώστε να μετράνε σωστά στις συγκρίσεις και στο budget.")
        group_names = list(EXPENSE_CATEGORIES.keys())
        with st.form("custom_cat_groups"):
            new_groups = {}
            for i, cat in enumerate(custom_cats):
                cat_exps = [e for e in data["expenses"] if e["category"] == cat]
                current = cat_exps[0]["group"]
                total = sum(e["amount"] for e in cat_exps)
                c_name, c_group = st.columns([3, 2])
                c_name.markdown(f"**{cat.strip()}**  \n{len(cat_exps)} δαπάνη/ες · {total:.2f} €")
                new_groups[cat] = c_group.selectbox("Ομάδα", group_names, index=group_names.index(current),
                                                    key=f"cg_{i}", label_visibility="collapsed")
            if st.form_submit_button("💾 Αποθήκευση Ομάδων"):
                for e in data["expenses"]:
                    if e["category"] in new_groups:
                        e["group"] = new_groups[e["category"]]
                save_data(data)
                st.success("✅ Οι ομάδες αποθηκεύτηκαν!")
                time.sleep(1.5)
                st.rerun()

    st.divider()

    # --- Budget ανά Ομάδα ---
    st.subheader("💼 Μηνιαίο Budget ανά Ομάδα")
    auto = auto_budgets(data["expenses"], now)
    saved_budgets = data.get("budgets", {})
    st.caption("Βάλε 0 σε μια ομάδα αν δεν θέλεις budget γι' αυτήν. "
               "Αν δεν έχεις αποθηκεύσει τίποτα, χρησιμοποιείται αυτόματα ο μέσος όρος των προηγούμενων μηνών.")
    with st.form("budgets_form"):
        new_budgets = {}
        bcols = st.columns(2)
        for i, g in enumerate(EXPENSE_CATEGORIES):
            default = float(saved_budgets.get(g, auto.get(g, 0.0)))
            hint = f"Μέσος όρος προηγ. μηνών: {auto[g]:.0f} €" if g in auto else "Δεν υπάρχει ιστορικό για αυτή την ομάδα"
            new_budgets[g] = bcols[i % 2].number_input(f"{g} (€)", min_value=0.0, value=default, step=10.0,
                                                       format="%.0f", help=hint, key=f"budget_{i}")
        if st.form_submit_button("💾 Αποθήκευση Budget"):
            # Αποθηκεύονται όλες οι ομάδες (και το 0) ώστε το 0 να σημαίνει "χωρίς budget"
            data["budgets"] = {g: v for g, v in new_budgets.items()}
            save_data(data)
            st.success("✅ Τα budget αποθηκεύτηκαν!")
            time.sleep(1.5)
            st.rerun()
    if saved_budgets and st.button("↺ Επαναφορά στα αυτόματα budget"):
        data["budgets"] = {}
        save_data(data)
        st.rerun()

    st.divider()
    st.subheader("🚨 Μηδενισμός Δεδομένων")
    st.warning("ΠΡΟΣΟΧΗ: Αυτή η ενέργεια θα διαγράψει οριστικά όλα τα έξοδα και θα μηδενίσει το ρευστό.")
    if 'confirm_reset' not in st.session_state: st.session_state.confirm_reset = False
    if not st.session_state.confirm_reset:
        if st.button("🚨 ΜΗΔΕΝΙΣΜΟΣ ΟΛΩΝ ΤΩΝ ΔΕΔΟΜΕΝΩΝ 🚨"):
            st.session_state.confirm_reset = True
            st.rerun()
    else:
        st.error("⚠️ Είστε σίγουρος/η; Αυτή η ενέργεια δεν μπορεί να αναιρεθεί!")
        col1, col2 = st.columns(2)
        if col1.button("✔️ Ναι, Οριστική Διαγραφή", type="primary"):
            data = {"liquidity": {"Μετρητά": 0.0, "Revolut": 0.0, "Πειραιώς": 0.0}, "expenses": [], "incomes": [], "liquidity_updates": [], "budgets": {}}
            save_data(data)
            st.session_state.confirm_reset = False
            st.success("✅ Όλα τα δεδομένα μηδενίστηκαν επιτυχώς!")
            time.sleep(1.5)
            st.rerun()
        if col2.button("❌ Άκυρο"):
            st.session_state.confirm_reset = False
            st.rerun()

# ==========================================
# 8. ΕΞΟΔΟΣ
# ==========================================
elif menu == "🚪 Έξοδος":
    st.title("Έξοδος από το Πρόγραμμα")
    st.info("💡 Ο πιο απλός τρόπος για να βγεις, είναι απλά να κλείσεις αυτήν την καρτέλα (tab) του browser. Τα δεδομένα σου αποθηκεύονται αυτόματα σε κάθε αλλαγή!")
    if st.button("🛑 Τερματισμός Εφαρμογής"):
        st.success("Ο server τερματίστηκε! Μπορείς να κλείσεις αυτή την καρτέλα με ασφάλεια.")
        os._exit(0)