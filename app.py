import streamlit as st
import pandas as pd
import pyodbc

# Set page configuration
st.set_page_config(page_title="Food Wastage Management System", layout="wide")

# Database connection function
@st.cache_resource
def init_connection():
    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=.;"
        "DATABASE=FoodWastageDB;"
        "Trusted_Connection=yes;"
        "MARS_Connection=yes;"  
    )
    
    return pyodbc.connect(conn_str)
    

try:
    conn = init_connection()
except Exception as e:
    st.error(f"Error connecting to database: {e}")
    conn = None

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", [
    "Dashboard Overview", 
    "Manage Food Listings", 
    "Providers & Receivers", 
    "Claims Tracking",
    "Analytical Insights (15 Queries)"  # <-- Add this option
])
# --- PAGE 1: DASHBOARD OVERVIEW ---
if page == "Dashboard Overview":
    st.title("📊 Food Wastage Management Dashboard")
    st.write("Real-time metrics and dynamic system analytics.")

    if conn:
        try:
            # Fetch fresh filter elements
            cities_list = pd.read_sql("SELECT DISTINCT Location FROM FoodListings", conn)["Location"].dropna().tolist()
            ptypes_list = pd.read_sql("SELECT DISTINCT Provider_Type FROM FoodListings", conn)["Provider_Type"].dropna().tolist()
            ftypes_list = pd.read_sql("SELECT DISTINCT Food_Type FROM FoodListings", conn)["Food_Type"].dropna().tolist()
            mtypes_list = pd.read_sql("SELECT DISTINCT Meal_Type FROM FoodListings", conn)["Meal_Type"].dropna().tolist()

            st.sidebar.markdown("---")
            st.sidebar.subheader("🔍 Global Dashboard Filters")
            
            selected_city = st.sidebar.selectbox("Filter by City/Location:", ["All"] + cities_list)
            selected_ptype = st.sidebar.selectbox("Filter by Provider Type:", ["All"] + ptypes_list)
            selected_ftype = st.sidebar.selectbox("Filter by Food Type:", ["All"] + ftypes_list)
            selected_mtype = st.sidebar.selectbox("Filter by Meal Type:", ["All"] + mtypes_list)

            # Build query with robust string formatting
            base_query = "SELECT * FROM FoodListings WHERE 1=1"
            query_params = []

            if selected_city != "All":
                base_query += " AND LOWER(TRIM(Location)) = LOWER(TRIM(?))"
                query_params.append(selected_city)
            if selected_ptype != "All":
                base_query += " AND LOWER(TRIM(Provider_Type)) = LOWER(TRIM(?))"
                query_params.append(selected_ptype)
            if selected_ftype != "All":
                base_query += " AND LOWER(TRIM(Food_Type)) = LOWER(TRIM(?))"
                query_params.append(selected_ftype)
            if selected_mtype != "All":
                base_query += " AND LOWER(TRIM(Meal_Type)) = LOWER(TRIM(?))"
                query_params.append(selected_mtype)

            filtered_df = pd.read_sql(base_query, conn, params=query_params)

            # Fallback logic if selection combo returns empty results
            if filtered_df.empty:
                st.warning(f"⚠️ No active records match the exact combination: **{selected_city}** + **{selected_ptype}** + **{selected_mtype}**.")
                st.info("ℹ️ Showing global database statistics below instead:")
                display_df = pd.read_sql("SELECT * FROM FoodListings", conn)
            else:
                display_df = filtered_df

            # Calculate metrics
            total_listings = len(display_df)
            total_qty = display_df['Quantity'].sum() if 'Quantity' in display_df.columns else 0
            total_locs = display_df['Location'].nunique() if 'Location' in display_df.columns else 0

            col1, col2, col3 = st.columns(3)
            col1.metric(label="Total Active Donations", value=f"{total_listings} Items")
            col2.metric(label="Total Food Volume", value=f"{total_qty} Units")
            col3.metric(label="Impacted Locations", value=f"{total_locs} Cities/Areas")
            
            st.markdown("---")
            st.subheader("💡 Supply Insights: Food Volume by Provider Type")
            if not display_df.empty and 'Provider_Type' in display_df.columns and 'Quantity' in display_df.columns:
                chart_data = display_df.groupby("Provider_Type")["Quantity"].sum().reset_index().set_index("Provider_Type")
                st.bar_chart(chart_data, color="#4CAF50")
            
            st.markdown("---")
            st.subheader("📋 Filtered Food Listings Log")
            st.dataframe(display_df, use_container_width=True)

        except Exception as e:
            st.error(f"Error loading dashboard metrics: {e}")
# --- PAGE 2: MANAGE FOOD LISTINGS (CRUD) ---
elif page == "Manage Food Listings":
    st.title("🍕 Manage Food Listings")
    
    # Sub-navigation for CRUD operations
    crud_action = st.radio("Select Operation", ["View Listings", "Add New Listing", "Update Listing", "Delete Listing"], horizontal=True)
    
   # --- 1. READ (View Listings with Interactive Search/Filter) ---
    if crud_action == "View Listings":
        st.subheader("Current Active Food Listings")
        if conn:
            try:
                # Force SQL Server to clear temporary read caches for this session
                cursor = conn.cursor()
                cursor.execute("SET NOCOUNT ON;") 
                
                # Add real-time text search and city drop-down filtering directly onto the viewing layout
                col_search, col_filter = st.columns([2, 1])
                
                with col_search:
                    search_term = st.text_input("🔍 Search listings by food item name:", "")
                with col_filter:
                    # Fetch fresh distinct locations
                    available_cities = pd.read_sql("SELECT DISTINCT Location FROM FoodListings", conn)["Location"].dropna().tolist()
                    filter_city = st.selectbox("📍 Quick Filter by City:", ["All Cities"] + available_cities)
                
                # Build dynamic viewing query - explicitly ordering by Food_ID descending 
                # so that newly added items show up instantly at the very top!
                view_query = "SELECT Food_ID, Food_Name, Quantity, Expiry_Date, Provider_ID, Provider_Type, Location, Food_Type, Meal_Type FROM FoodListings WHERE 1=1"
                params = []
                
                if search_term:
                    view_query += " AND Food_Name LIKE ?"
                    params.append(f"%{search_term}%")
                if filter_city != "All Cities":
                    view_query += " AND Location = ?"
                    params.append(filter_city)
                
                # Append explicit ordering
                view_query += " ORDER BY Food_ID DESC"
                    
                df = pd.read_sql(view_query, conn, params=params)
                
                if not df.empty:
                    # =================================================================
                    # FIX: Using 'Int64' (Capital I) which allows clean integer rendering 
                    # even if there are missing or NULL values present.
                    # =================================================================
                    if "Food_ID" in df.columns:
                        df["Food_ID"] = df["Food_ID"].astype("Int64")
                    if "Provider_ID" in df.columns:
                        df["Provider_ID"] = df["Provider_ID"].astype("Int64")
                    # =================================================================
                        
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No active food listings match your current search terms or city filters.")
            except Exception as view_err:
                st.error(f"Error loading active directory views: {view_err}")
    # --- 2. CREATE (Add New Listing with Auto-Location) ---
    elif crud_action == "Add New Listing":
        st.subheader("Add a New Food Entry")
        
        if conn:
            try:
                # Fetch ID, Name, Type, AND City from the Providers directory
                providers_df = pd.read_sql("SELECT Provider_ID, Name, Type, City FROM Providers", conn)
                
                if not providers_df.empty:
                    # Create a clear option label for the dropdown
                    providers_df['Display_Name'] = (
                        providers_df['Provider_ID'].astype(str) + " - " + 
                        providers_df['Name'] + " (" + providers_df['Type'] + ") | City: " + providers_df['City']
                    )
                    provider_options = providers_df['Display_Name'].tolist()
                else:
                    provider_options = []
                    st.error("⚠️ No registered providers found. Please populate your Providers table first.")
                
                with st.form("add_listing_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        food_name = st.text_input("Food Name (e.g., Rice, Vegetables)")
                        quantity = st.number_input("Quantity", min_value=1, step=1)
                        expiry_date = st.date_input("Expiry Date")
                    with col2:
                        selected_provider_str = st.selectbox("Select Registered Provider:", provider_options)
                        st.caption("ℹ️ *The location profile city will automatically sync from the provider's official registration table.*")
                    
                    col3, col4 = st.columns(2)
                    with col3:
                        food_type = st.selectbox("Food Type", ["Vegetarian", "Non-Vegetarian", "Vegan"])
                    with col4:
                        meal_type = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snacks"])
                        
                    submit_btn = st.form_submit_button("Submit Entry")
                    
                    if submit_btn and selected_provider_str:
                        # Find exactly which provider was picked
                        selected_idx = provider_options.index(selected_provider_str)
                        true_provider_id = int(providers_df['Provider_ID'].iloc[selected_idx])
                        true_provider_type = providers_df['Type'].iloc[selected_idx]
                        
                        # HERE IS THE AUTO-FIX: Grab the city directly from the provider's master file data row!
                        auto_location = providers_df['City'].iloc[selected_idx]
                        
                        try:
                            cursor = conn.cursor()
                            insert_query = """
                                INSERT INTO FoodListings (Food_Name, Quantity, Expiry_Date, Provider_ID, Provider_Type, Location, Food_Type, Meal_Type)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """
                            cursor.execute(insert_query, (
                                food_name, 
                                quantity, 
                                str(expiry_date), 
                                true_provider_id, 
                                true_provider_type, 
                                auto_location, # Safely map the verified corporate location city 
                                food_type, 
                                meal_type
                            ))
                            conn.commit()
                            st.success(f"🎉 Successfully added '{food_name}'! Location set automatically to '{auto_location}' via Provider details.")
                        except Exception as e:
                            st.error(f"Failed to save listing record to SQL Server: {e}")
                            
            except Exception as outer_err:
                st.error(f"Error loading system profile registries: {outer_err}")
    # --- 3. UPDATE (Edit Listing) ---
    elif crud_action == "Update Listing":
        st.subheader("Update an Existing Food Entry")
        if conn:
            # Let the user pick which Food ID to update
            food_ids = pd.read_sql("SELECT Food_ID FROM FoodListings", conn)["Food_ID"].tolist()
            selected_id = st.selectbox("Select Food ID to Update", food_ids)
            
            if selected_id:
                # Fetch current details of selected item
                current_data = pd.read_sql(f"SELECT * FROM FoodListings WHERE Food_ID = {selected_id}", conn).iloc[0]
                
                with st.form("update_listing_form"):
                    new_name = st.text_input("Food Name", value=current_data["Food_Name"])
                    new_qty = st.number_input("Quantity", min_value=1, value=int(current_data["Quantity"]))
                    new_loc = st.text_input("Location", value=current_data["Location"])
                    
                    update_btn = st.form_submit_button("Update Records")
                    
                    if update_btn:
                        try:
                            cursor = conn.cursor()
                            update_query = """
                                UPDATE FoodListings 
                                SET Food_Name = ?, Quantity = ?, Location = ?
                                WHERE Food_ID = ?
                            """
                            cursor.execute(update_query, (new_name, new_qty, new_loc, selected_id))
                            conn.commit()
                            st.success(f"✅ Food ID {selected_id} updated successfully!")
                        except Exception as e:
                            st.error(f"Update failed: {e}")

    # --- 4. DELETE (Remove Listing) ---
    elif crud_action == "Delete Listing":
        st.subheader("Remove a Food Entry")
        if conn:
            food_ids = pd.read_sql("SELECT Food_ID FROM FoodListings", conn)["Food_ID"].tolist()
            delete_id = st.selectbox("Select Food ID to permanently delete", food_ids)
            
            # Warning block for safety
            st.warning(f"Are you sure you want to delete Food ID {delete_id}? This action cannot be undone.")
            delete_btn = st.button("🔴 Confirm Delete")
            
            if delete_btn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(f"DELETE FROM FoodListings WHERE Food_ID = {delete_id}")
                    conn.commit()
                    st.success(f"🗑️ Food ID {delete_id} has been deleted.")
                except Exception as e:
                    st.error(f"Delete failed: {e}")

# --- PAGE 3: PROVIDERS & RECEIVERS ---
elif page == "Providers & Receivers":
    st.title("👥 Stakeholder Directories")
    st.write("View and search directory structures for ecosystem partners.")
    
    if conn:
        try:
            tab1, tab2 = st.tabs(["🏭 Food Providers Directory", "🏠 Food Receivers Directory"])
            
            with tab1:
                st.subheader("Registered Providers Master Database")
                
                # Fetch fresh contact records from SQL Server
                prov_df = pd.read_sql("SELECT * FROM Providers", conn)
                
                if not prov_df.empty:
                    # -----------------------------------------------------------------
                    # INTERACTIVE SEARCH WINDOW INTEGRATION
                    # -----------------------------------------------------------------
                    st.markdown("### 🔍 Live Provider Search Window")
                    search_query = st.text_input(
                        "Search provider directory by Name, Contact Number, Address, or City...", 
                        placeholder="Type here to filter records instantly..."
                    )
                    
                    # Apply real-time string filtering across all logical descriptive columns
                    if search_query:
                        filtered_prov_df = prov_df[
                            prov_df['Name'].astype(str).str.contains(search_query, case=False, na=False) |
                            prov_df['City'].astype(str).str.contains(search_query, case=False, na=False) |
                            prov_df['Address'].astype(str).str.contains(search_query, case=False, na=False) |
                            prov_df['Contact'].astype(str).str.contains(search_query, case=False, na=False) |
                            prov_df['Type'].astype(str).str.contains(search_query, case=False, na=False)
                        ]
                        st.caption(f"Showing {len(filtered_prov_df)} matching contact records:")
                        st.dataframe(filtered_prov_df, use_container_width=True, hide_index=True)
                    else:
                        # Default state: display full directory if search bar is empty
                        st.caption(f"Showing all {len(prov_df)} registered corporate providers:")
                        st.dataframe(prov_df, use_container_width=True, hide_index=True)
                    # -----------------------------------------------------------------
                    
                    # Small structural metric insights below the search view
                    if "Type" in prov_df.columns:
                        st.markdown("---")
                        st.markdown("#### 📊 Ecosystem Distribution by Organization Type")
                        st.write(prov_df["Type"].value_counts())
                else:
                    st.info("The Provider registration table is currently empty in SQL Server.")
            
            with tab2:
                st.subheader("Registered Receivers / NGOs Details")
                recv_df = pd.read_sql("SELECT * FROM Receivers", conn)
                
                if not recv_df.empty:
                    st.dataframe(recv_df, use_container_width=True, hide_index=True)
                else:
                    st.info("The Receivers registration table is currently empty.")
                
        except Exception as e:
            st.error(f"Could not load stakeholder data: {e}")
# --- PAGE 4: CLAIMS TRACKING ---
elif page == "Claims Tracking":
    st.title("📋 Claims Optimization & Fulfillment Pipeline")
    st.write("Connect available surplus food listings directly to registered receivers in need.")
    
    if conn:
        # Re-establishing your original dual-tab structure
        claim_tab1, claim_tab2 = st.tabs(["🛒 Make a Food Claim", "📦 View Logistics Pipeline"])
        
        # --- TAB 1: MAKE A FOOD CLAIM ---
        with claim_tab1:
            st.subheader("Reserve Available Food Surplus")
            try:
                # Fetch detailed rows so the user can actually see what they are claiming
                active_listings_df = pd.read_sql("SELECT Food_ID, Food_Name, Quantity, Location FROM FoodListings ORDER BY Food_ID DESC", conn)
                receivers_df = pd.read_sql("SELECT Receiver_ID, Name, City FROM Receivers", conn)
                
                active_listings_df = active_listings_df.dropna(subset=['Food_ID'])
                receivers_df = receivers_df.dropna(subset=['Receiver_ID'])
                
                if not active_listings_df.empty and not receivers_df.empty:
                    # RESTORED: Maps your rich descriptive text to the true underlying database IDs
                    food_options_dict = {
                        f"ID: {int(row['Food_ID'])} | {row['Food_Name']} ({row['Quantity']} units) - {row['Location']}": int(row['Food_ID']) 
                        for _, row in active_listings_df.iterrows()
                    }
                    receiver_options_dict = {
                        f"ID: {int(row['Receiver_ID'])} | {row['Name']} ({row['City']})": int(row['Receiver_ID']) 
                        for _, row in receivers_df.iterrows()
                    }
                    
                    # Your original form layout structure
                    with st.form("claims_entry_form", clear_on_submit=True):
                        selected_food_lbl = st.selectbox("Choose Available Food Item:", list(food_options_dict.keys()))
                        selected_receiver_lbl = st.selectbox("Select Requesting NGO / Receiver:", list(receiver_options_dict.keys()))
                        claim_status = st.selectbox("Initial Logistics Status:", ["Pending", "Completed"])
                        submit_claim_btn = st.form_submit_button("Confirm & Reserve Food")
                        
                        if submit_claim_btn:
                            # Extracting the true integer keys from your labels
                            chosen_food_id = food_options_dict[selected_food_lbl]
                            chosen_receiver_id = receiver_options_dict[selected_receiver_lbl]
                            
                            cursor = conn.cursor()
                            cursor.execute("BEGIN TRANSACTION;")
                            
                            try:
                                # 1. FETCH CURRENT HIGHEST ID AND INCREMENT IT BY 1
                                cursor.execute("SELECT ISNULL(MAX(Claim_ID), 0) FROM Claims")
                                max_id = cursor.fetchone()[0]
                                next_claim_id = int(max_id) + 1
                                
                                # Safeguard to push past your existing 1000 records if needed
                                if next_claim_id <= 1000 and not active_listings_df.empty:
                                    next_claim_id = 1001
                                
                                # 2. INSERT EXPLICITLY WITH THE NEW INCREMENTED ID
                                insert_query = """
                                    INSERT INTO Claims (Claim_ID, Food_ID, Receiver_ID, Status, Timestamp) 
                                    VALUES (?, ?, ?, ?, GETDATE())
                                """
                                cursor.execute(insert_query, (next_claim_id, chosen_food_id, chosen_receiver_id, claim_status))
                                conn.commit()
                                
                                # Cache the triggers in session state so they fire post-refresh
                                st.session_state["claim_success_msg"] = f"🎉 Success! Claim ID {next_claim_id} logged for Food Item ID {chosen_food_id}!"
                                st.session_state["show_balloons"] = True
                                
                            except Exception as db_err:
                                conn.rollback()
                                st.error(f"❌ Database Write Error: {db_err}")
                            finally:
                                cursor.close()
                            
                            st.rerun()
                else:
                    st.warning("Cannot process claims: No valid listings or receivers found inside database tables.")
            except Exception as claim_err:
                st.error(f"Error initializing interactive claim interface components: {claim_err}")
                
        # --- TAB 2: VIEW LOGISTICS PIPELINE ---
        with claim_tab2:
            st.subheader("Active Logistics Tracking Ledger")
            try:
                # Force ordering by Claim_ID DESC to push the highest incremented keys to row #1
                query = """
                    SELECT 
                        Claim_ID AS [Claim ID],
                        Food_ID AS [Food ID],
                        Receiver_ID AS [Receiver ID],
                        Status AS [Logistics Status],
                        Timestamp AS [Logged Timestamp]
                    FROM Claims 
                    ORDER BY Claim_ID DESC
                """
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                columns = [column[0] for column in cursor.description]
                claims_df = pd.DataFrame.from_records(rows, columns=columns)
                
                if not claims_df.empty:
                    # Ensure numeric IDs don't render with strange decimal points
                    for col in ["Claim ID", "Food ID", "Receiver ID"]:
                        if col in claims_df.columns:
                            claims_df[col] = pd.to_numeric(claims_df[col], errors='coerce').astype("Int64")
                    
                    # 2026 Layout Standard: Kept clean, floats new IDs to the top, hides empty Pandas indices
                    st.dataframe(claims_df, width='stretch', hide_index=True)
                    
                    st.markdown("---")
                    st.subheader("🔍 Quick Status Filter")
                    unique_statuses = claims_df["Logistics Status"].dropna().unique().tolist()
                    selected_status = st.selectbox("Sift records by operational status context:", ["All Statuses"] + unique_statuses)
                    if selected_status != "All Statuses":
                        filtered_df = claims_df[claims_df["Logistics Status"] == selected_status]
                        st.dataframe(filtered_df, width='stretch', hide_index=True)
                else:
                    st.info("The Claims ledger is currently empty. Submit an entry on Tab 1!")
            except Exception as e:
                st.error(f"Could not load tracking ledger pipelines: {e}")

    # Session state UI triggers
    if "claim_success_msg" in st.session_state:
        st.success(st.session_state["claim_success_msg"])
        st.toast(st.session_state["claim_success_msg"], icon="✅")
        del st.session_state["claim_success_msg"]
    if "show_balloons" in st.session_state:
        st.balloons()
        del st.session_state["show_balloons"]
        
        
# --- PAGE 5: ANALYTICAL INSIGHTS (15 REQUIRED QUERIES) ---
elif page == "Analytical Insights (15 Queries)":
    st.title("🔬 Deep-Dive SQL Analytics & Trends")
    st.write("Review execution codes and real-time data reports for the 15 required evaluation queries.")

    if conn:
        # Dictionary setup mapping questions to queries for clean selection
        queries_dict = {
            "1. Providers & Receivers distribution per city": """
                SELECT  ISNULL(p.City, r.City) AS City,
                COUNT(DISTINCT p.Provider_ID) AS Total_Providers,
                COUNT(DISTINCT r.Receiver_ID) AS Total_Receivers
                FROM Providers p FULL OUTER JOIN Receivers r ON p.City = r.City
                GROUP BY ISNULL(p.City, r.City)
                ORDER BY City;
            """,
            "2. Top contributing food provider type": """
                SELECT Provider_Type, SUM(Quantity) AS Total_Quantity_Contributed
                FROM FoodListings
                GROUP BY Provider_Type
                ORDER BY Total_Quantity_Contributed DESC;
            """,
            "3. Dynamic provider contact lookups by city": """
                SELECT Name, Type, Address, Contact, City 
                FROM Providers 
                WHERE City = ?;
            """,
            "4. Highly active receivers by claims count": """
                SELECT r.Name, r.Type, COUNT(c.Claim_ID) AS Total_Claims_Made
                FROM Receivers r
                JOIN Claims c ON r.Receiver_ID = c.Receiver_ID
                GROUP BY r.Name, r.Type
                ORDER BY Total_Claims_Made DESC;
            """,
            "5. Total aggregate quantity of food available": """
                SELECT SUM(Quantity) AS Total_Available_Food FROM FoodListings;
            """,
            "6. City with the highest listing volume footprint": """
                SELECT Location AS City, COUNT(Food_ID) AS Total_Listings
                FROM FoodListings
                GROUP BY Location
                ORDER BY Total_Listings DESC;
            """,
            "7. Most common food types distribution": """
                SELECT Food_Type, COUNT(*) AS Listing_Count, SUM(Quantity) AS Total_Units
                FROM FoodListings
                GROUP BY Food_Type
                ORDER BY Listing_Count DESC;
            """,
            "8. Total food metrics donated per distinct provider": """
                SELECT p.Name, p.Type, SUM(f.Quantity) AS Total_Donated_Quantity
                FROM Providers p
                JOIN FoodListings f ON p.Provider_ID = f.Provider_ID
                GROUP BY p.Name, p.Type
                ORDER BY Total_Donated_Quantity DESC;
            """,
            "9. Total claims made against specific items": """
                SELECT f.Food_Name, COUNT(c.Claim_ID) AS Total_Claims
                FROM FoodListings f
                LEFT JOIN Claims c ON f.Food_ID = c.Food_ID
                GROUP BY f.Food_Name
                ORDER BY Total_Claims DESC;
            """,
            "10. Provider linked with most completed success claims": """
                SELECT p.Name, COUNT(c.Claim_ID) AS Successful_Claims
                FROM Providers p
                JOIN FoodListings f ON p.Provider_ID = f.Provider_ID
                JOIN Claims c ON f.Food_ID = c.Food_ID
                WHERE c.Status = 'Completed'
                GROUP BY p.Name
                ORDER BY Successful_Claims DESC;
            """,
            "11. Claims status breakdown percentages (Completed vs Pending)": """
                SELECT Status, 
                       COUNT(*) AS Total_Count,
                       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Claims), 2) AS Percentage
                FROM Claims
                GROUP BY Status;
            """,
            "12. Average items size claimed per receiver target": """
                SELECT r.Name, AVG(CAST(f.Quantity AS FLOAT)) AS Avg_Quantity_Claimed
                FROM Receivers r
                JOIN Claims c ON r.Receiver_ID = c.Receiver_ID
                JOIN FoodListings f ON c.Food_ID = f.Food_ID
                GROUP BY r.Name;
            """,
            "13. Most highly demanded target meal type classification": """
                SELECT f.Meal_Type, COUNT(c.Claim_ID) AS Total_Claims
                FROM FoodListings f
                JOIN Claims c ON f.Food_ID = c.Food_ID
                GROUP BY f.Meal_Type
                ORDER BY Total_Claims DESC;
            """,
            "14. Critical tracking alert: Food items expiring inside 3 days": """
                SELECT Food_Name, Quantity, Expiry_Date, Location 
                FROM FoodListings 
                WHERE Expiry_Date BETWEEN GETDATE() AND DATEADD(day, 3, GETDATE())
                ORDER BY Expiry_Date ASC;
            """,
            "15. Matrix distribution: Total item volume grouped by City + Meal Type": """
                SELECT Location AS City, Meal_Type, SUM(Quantity) AS Distributed_Volume
                FROM FoodListings
                GROUP BY Location, Meal_Type
                ORDER BY Location, Distributed_Volume DESC;
            """
        }

        # Dropdown selection for evaluation clarity
        selected_metric = st.selectbox("Select a metric query to run:", list(queries_dict.keys()))
        raw_sql = queries_dict[selected_metric]

        st.markdown("### 💻 SQL Execution Code")
        st.code(raw_sql, language="sql")

        try:
            # Special input argument execution context for Query #3
            if "Query #3" in selected_metric or "Dynamic provider contact" in selected_metric:
                cities_list = pd.read_sql("SELECT DISTINCT City FROM Providers", conn)["City"].tolist()
                if cities_list:
                    chosen_city = st.selectbox("Select a target city to filter contacts:", cities_list)
                    result_df = pd.read_sql(raw_sql, conn, params=[chosen_city])
                else:
                    st.info("No provider locations indexed to filter.")
                    result_df = pd.DataFrame()
            else:
                result_df = pd.read_sql(raw_sql, conn)

            st.markdown("### 📊 Query Data Result Table")
            if not result_df.empty:
                st.dataframe(result_df, use_container_width=True)
            else:
                st.warning("Query executed successfully but returned zero active records.")

        except Exception as err:
            st.error(f"Database engine parsing execution exception: {err}")