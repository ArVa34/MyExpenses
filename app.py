import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
import time
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

st.set_page_config(page_title="Οργάνωση Εξόδων", page_icon="💶", layout="wide")

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "incomes" not in data:
                data["incomes"] = []
            return data
    else:
        return {"liquidity": {"Μετρητά": 0.0, "Revolut": 0.0, "Πειραιώς": 0.0}, "expenses": [], "incomes": [], "liquidity_updates": []}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

data = load_data()

# --- Υπολογισμοί Μηνιαίας Σύγκρισης ---
now = datetime.now()
curr_month, curr_year = now.month, now.year
prev_month = 12 if curr_month == 1 else curr_month - 1
prev_year = curr_year - 1 if curr_month == 1 else curr_year

curr_month_exp = 0.0
prev_month_exp = 0.0
weekly_expenses = 0.0

for exp in data["expenses"]:
    try:
        exp_date = datetime.strptime(exp["date"], "%d/%m/%Y")
        if exp_date.month == curr_month and exp_date.year == curr_year:
            curr_month_exp += exp["amount"]
        elif exp_date.month == prev_month and exp_date.year == prev_year:
            prev_month_exp += exp["amount"]
            
        if 0 <= (now - exp_date).days <= 7:
            weekly_expenses += exp["amount"]
    except ValueError:
        pass

curr_month_inc = 0.0
prev_month_inc = 0.0
for inc in data["incomes"]:
    try:
        inc_date = datetime.strptime(inc["date"], "%d/%m/%Y")
        if inc_date.month == curr_month and inc_date.year == curr_year:
            curr_month_inc += inc["amount"]
        elif inc_date.month == prev_month and inc_date.year == prev_year:
            prev_month_inc += inc["amount"]
    except ValueError:
        pass

total_liquidity = sum(data["liquidity"].values())
exp_delta = curr_month_exp - prev_month_exp
inc_delta = curr_month_inc - prev_month_inc

st.sidebar.title("Γεια σου, Γιάννη! 👋")
st.sidebar.write("Επίλεξε λειτουργία:")
menu = st.sidebar.radio("", ["🏠 Dashboard", "💰 Ενημέρωση Ρευστότητας", "⬇️ Καταγραφή Εσόδου", "🛒 Καταγραφή Δαπάνης", "✏️ Επεξεργασία Δαπάνης", "📊 Ιστορικό & Εξαγωγή", "⚙️ Ρυθμίσεις (Reset)", "🚪 Έξοδος"])

# ==========================================
# 1. DASHBOARD
# ==========================================
if menu == "🏠 Dashboard":
    st.title("Συνοπτική Εικόνα Οικονομικών")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Συνολικό Ρευστό", f"{total_liquidity:.2f} €")
    col2.metric("Έσοδα Τρέχοντος Μήνα", f"{curr_month_inc:.2f} €", f"{inc_delta:+.2f} € από προηγ. μήνα")
    col3.metric("Έξοδα Τρέχοντος Μήνα", f"{curr_month_exp:.2f} €", f"{exp_delta:+.2f} € από προηγ. μήνα", delta_color="inverse")
    col4.metric("Έξοδα (7 Ημερών)", f"{weekly_expenses:.2f} €")
    
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
        df_exp = pd.DataFrame(data["expenses"])
        df_exp['parsed_date'] = pd.to_datetime(df_exp['date'], format='%d/%m/%Y')
        df_exp['month_year'] = df_exp['parsed_date'].dt.strftime('%m/%Y')
        
        # Αντιστοίχιση κάθε δαπάνης στην Οικογένειά της (Parent Category) για το γράφημα
        def get_parent_cat(subcat):
            for p, subs in EXPENSE_CATEGORIES.items():
                if subcat in subs: return p
            return "Άλλα"
        df_exp['parent_category'] = df_exp['category'].apply(get_parent_cat)
        
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
            st.subheader("Σοβαρότητα Εξόδων (Συνολικά)")
            necessity_sum = df_exp.groupby("necessity")["amount"].sum().reset_index()
            fig_nec = px.pie(necessity_sum, values='amount', names='necessity', hole=0.4)
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
        category = st.selectbox("Είδος Δαπάνης", EXPENSE_CATEGORIES[parent_cat])
        
    other_category = st.text_input("Περιέγραψε την δαπάνη (π.χ. Δώρο γενεθλίων):") if category == "Άλλες Δαπάνες" else ""
    
    location = st.text_input("Τοποθεσία (π.χ. Αθήνα)")
    amount = st.number_input("Ποσό Δαπάνης (€)", min_value=0.01, step=0.5, format="%.2f")
    pay_method = st.selectbox("Τρόπος Πληρωμής", ["Μετρητά", "Revolut", "Τράπεζα Πειραιώς", "Άλλος τρόπος"])
    other_pay_method = st.text_input("Περιέγραψε τον τρόπο πληρωμής:") if pay_method == "Άλλος τρόπος" else ""
    necessity = st.selectbox("Πόσο σοβαρή ήταν η δαπάνη;", ["Ανάγκη", "Θα μπορούσε μην είχε γίνει η δαπάνη αυτή", "Δεν έπρεπε να γίνει η δαπάνη αυτή"])
    
    if st.button("Καταχώρηση Δαπάνης"):
        final_category = other_category if category == "Άλλες Δαπάνες" else category
        final_pay_method = other_pay_method if pay_method == "Άλλος τρόπος" else pay_method
        mapped_method = "Πειραιώς" if final_pay_method == "Τράπεζα Πειραιώς" else final_pay_method
        if mapped_method in data["liquidity"]: data["liquidity"][mapped_method] -= amount
        data["expenses"].append({
            "date": date_input.strftime("%d/%m/%Y"), "category": final_category,
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
            
            # Εντοπισμός Ομάδας βάσει της υπάρχουσας δαπάνης
            def get_parent_and_sub(category_name):
                for p, subs in EXPENSE_CATEGORIES.items():
                    if category_name in subs: return p, category_name
                return "Άλλα", "Άλλες Δαπάνες"
                
            p_val, s_val = get_parent_and_sub(exp_to_edit["category"])
            
            col_p, col_s = st.columns(2)
            with col_p:
                p_idx = list(EXPENSE_CATEGORIES.keys()).index(p_val)
                new_parent_cat = st.selectbox("Ομάδα Δαπανών", list(EXPENSE_CATEGORIES.keys()), index=p_idx)
            with col_s:
                sub_opts = EXPENSE_CATEGORIES[new_parent_cat]
                s_idx = sub_opts.index(s_val) if s_val in sub_opts else 0
                new_category = st.selectbox("Είδος Δαπάνης", sub_opts, index=s_idx)
                
            new_other_category = ""
            if new_category == "Άλλες Δαπάνες":
                default_custom = exp_to_edit["category"] if exp_to_edit["category"] not in sum(EXPENSE_CATEGORIES.values(), []) else ""
                new_other_category = st.text_input("Περιέγραψε την δαπάνη:", value=default_custom)
                
            new_location = st.text_input("Τοποθεσία", value=exp_to_edit["location"])
            new_amount = st.number_input("Ποσό Δαπάνης (€)", min_value=0.01, step=0.5, value=float(exp_to_edit["amount"]), format="%.2f")
            
            pay_methods = ["Μετρητά", "Revolut", "Τράπεζα Πειραιώς", "Άλλος τρόπος"]
            pm_idx = pay_methods.index(exp_to_edit["payment_method"]) if exp_to_edit["payment_method"] in pay_methods else 3
            new_pay_method = st.selectbox("Τρόπος Πληρωμής", pay_methods, index=pm_idx)
            new_other_pay_method = st.text_input("Περιέγραψε τον τρόπο πληρωμής:", value=exp_to_edit["payment_method"] if pm_idx == 3 else "") if new_pay_method == "Άλλος τρόπος" else ""
            necessities = ["Ανάγκη", "Θα μπορούσε μην είχε γίνει η δαπάνη αυτή", "Δεν έπρεπε να γίνει η δαπάνη αυτή"]
            nec_idx = necessities.index(exp_to_edit["necessity"]) if exp_to_edit["necessity"] in necessities else 0
            new_necessity = st.selectbox("Πόσο σοβαρή ήταν η δαπάνη;", necessities, index=nec_idx)
            
            col1, col2 = st.columns(2)
            if col1.button("💾 Αποθήκευση Αλλαγών"):
                final_category = new_other_category if new_category == "Άλλες Δαπάνες" else new_category
                final_pay_method = new_other_pay_method if new_pay_method == "Άλλος τρόπος" else new_pay_method
                old_pay_method, old_amount = exp_to_edit["payment_method"], exp_to_edit["amount"]
                mapped_old_pm = "Πειραιώς" if old_pay_method == "Τράπεζα Πειραιώς" else old_pay_method
                if mapped_old_pm in data["liquidity"]: data["liquidity"][mapped_old_pm] += old_amount
                mapped_new_pm = "Πειραιώς" if final_pay_method == "Τράπεζα Πειραιώς" else final_pay_method
                if mapped_new_pm in data["liquidity"]: data["liquidity"][mapped_new_pm] -= new_amount
                data["expenses"][selected_idx] = {
                    "date": new_date.strftime("%d/%m/%Y"), "category": final_category, "location": new_location,
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
        df = pd.DataFrame(data["expenses"])
        df['parsed_date'] = pd.to_datetime(df['date'], format='%d/%m/%Y')
        df['month_year'] = df['parsed_date'].dt.strftime('%m/%Y')

        def get_parent_cat_hist(subcat):
            for p, subs in EXPENSE_CATEGORIES.items():
                if subcat in subs: return p
            return "Άλλα"
        df['parent_category'] = df['category'].apply(get_parent_cat_hist)

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
# 7. ΡΥΘΜΙΣΕΙΣ / ΜΗΔΕΝΙΣΜΟΣ
# ==========================================
elif menu == "⚙️ Ρυθμίσεις (Reset)":
    st.title("Ρυθμίσεις Δεδομένων")
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
            data = {"liquidity": {"Μετρητά": 0.0, "Revolut": 0.0, "Πειραιώς": 0.0}, "expenses": [], "incomes": [], "liquidity_updates": []}
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