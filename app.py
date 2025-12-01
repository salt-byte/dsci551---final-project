import streamlit as st
import json
import pandas as pd
import plotly.express as px
import re
from collections import defaultdict

# ============================================================================
# JSON Tokenizer & Parser (from final_code.ipynb)
# ============================================================================


class Token:
    #Represents a JSON token with type, value, and position.
    def __init__(self, t, v, pos):
        self.type, self.value, self.pos = t, v, pos

class Tokenizer:
    ws = set(" \t\r\n")
    def __init__(self, text):
        self.text, self.n, self.i = text, len(text), 0

    def peek(self):
        return self.text[self.i] if self.i < self.n else ''

    def next(self):
        ch = self.peek()
        self.i += 1
        return ch

    def skip_ws(self):
        while self.i < self.n and self.text[self.i] in self.ws:
            self.i += 1

    def read_str(self, start):
        self.next()  # skip opening quote
        out = []
        while True:
            if self.i >= self.n:
                raise SyntaxError(f"String not closed (from {start})")
            ch = self.next()
            if ch == '"':
                break
            if ch == '\\':
                if self.i >= self.n:
                    raise SyntaxError("Bad escape sequence")
                esc = self.next()
                m = {'"':'"', '\\':'\\', '/':'/', 'b':'\b', 'f':'\f', 'n':'\n', 'r':'\r', 't':'\t'}
                if esc in m:
                    out.append(m[esc])
                else:
                    raise SyntaxError(f"Unknown escape \\{esc}")
            else:
                out.append(ch)
        return ''.join(out)

    def read_num(self, start):
        j = self.i
        if self.peek() == '-':
            self.next()
        if self.peek() == '0':
            self.next()
        else:
            if not self.peek().isdigit():
                raise SyntaxError(f"Bad number at {start}")
            while self.peek().isdigit():
                self.next()
        if self.peek() == '.':
            self.next()
            if not self.peek().isdigit():
                raise SyntaxError("Bad decimal")
            while self.peek().isdigit():
                self.next()
        s = self.text[j:self.i]
        return float(s) if '.' in s else int(s)

    def read_kw(self, start): #read keyword:true, false,null 
        for k, v in [("true", True), ("false", False), ("null", None)]:
            if self.text.startswith(k, self.i):
                self.i += len(k)
                return v
        raise SyntaxError(f"Unknown literal near {start}")

    def tokens(self):
        while True:
            self.skip_ws()
            if self.i >= self.n:
                yield Token("EOF", None, self.i) #end of file
                return
            ch = self.peek()
            pos = self.i
            if ch in '{}[]:,':
                self.next()
                yield Token(ch, ch, pos)
            elif ch == '"':
                yield Token("STR", self.read_str(pos), pos)#string
            elif ch in '-0123456789':
                yield Token("NUM", self.read_num(pos), pos)#number
            else:
                yield Token("KW", self.read_kw(pos), pos)#keyword

#focus on the relationship between tokens
class Stream:
    def __init__(self, tokenizer):
        self.gen, self.buf = tokenizer.tokens(), []

    def peek(self):
        if not self.buf:
            self.buf.append(next(self.gen))
        return self.buf[0]

    def next(self):
        if self.buf:
            return self.buf.pop(0)
        return next(self.gen)

    def expect(self, t):
        tok = self.next()
        if tok.type != t:
            raise SyntaxError(f"Expect {t} at {tok.pos}, got {tok.type}")
        return tok

class Parser:
    def parse(self, text):
        ts = Stream(Tokenizer(text))
        val = self.value(ts)
        if ts.peek().type != "EOF":
            raise SyntaxError("Extra content after JSON")
        return val

    def value(self, ts):
        t = ts.peek()
        if t.type == '{': return self.obj(ts)
        if t.type == '[': return self.arr(ts)
        if t.type == 'STR': return ts.next().value
        if t.type == 'NUM': return ts.next().value
        if t.type == 'KW':  return ts.next().value
        raise SyntaxError(f"Unexpected token {t.type}")

    def obj(self, ts):
        ts.expect('{')
        o = {}
        if ts.peek().type == '}':
            ts.next()
            return o
        while True:
            k = ts.expect("STR").value
            ts.expect(':')
            o[k] = self.value(ts)
            t = ts.peek()
            if t.type == ',':
                ts.next()
            elif t.type == '}':
                ts.next(); break
            else:
                raise SyntaxError(f"Unexpected {t.type}")
        return o

    def arr(self, ts):
        ts.expect('[')
        a = []
        if ts.peek().type == ']':
            ts.next()
            return a
        while True:
            a.append(self.value(ts))
            t = ts.peek()
            if t.type == ',':
                ts.next()
            elif t.type == ']':
                ts.next(); break
            else:
                raise SyntaxError(f"Unexpected {t.type}")
        return a

# ============================================================================
# Collection Class (from final_code.ipynb)
# ============================================================================

class Collection:

    def __init__(self, data):
        self.data = data if isinstance(data, list) else [data]#ensure that data is a list or turned to be a list
    
    def _extract_key(self, doc, key):
        """supports dot notation"""
        ks = key.split(".")
        cur = doc
        for k in ks:
            if not isinstance(cur, dict) or k not in cur:
                return None
            cur = cur[k]
        return cur

    def find(self, query=None):#query like{"attitude_count":500,"likes":2}
        
        if query is None:#find all data
            return self.data

        def match(doc, query): #to check if doc fits query
            for key, value in query.items():
                cur = self._extract_key(doc, key)  
                if cur != value:
                    return False
            return True

        return [doc for doc in self.data if match(doc, query)]

    def project(self, fields):

    #Return documents with only selected fields.
    #Example: fields = ["user", "text"]

        result = []
        for doc in self.data:
            projected = {}
            for field in fields:
                #use _extract_key to process nested key
                projected[field] = self._extract_key(doc, field)
            result.append(projected)
        return result

    def groupby(self, key):
        groups = {}
        for doc in self.data:
            group_value = self._extract_key(doc, key) 
            groups.setdefault(group_value, []).append(doc)
        return groups

    def aggregate(self, group_key, agg_func):
        #Apply an aggregation function (sum, count, avg, etc.) on each group.
        grouped = self.groupby(group_key)
        result = {}
        for k, docs in grouped.items():
            result[k] = agg_func(docs)
        return result


    def hash_join(self, other, key_self, key_other, join_type="inner"):
        """
        join_type: inner / left / right / full
        """

        # Build hash map for other
        hashmap = {}
        for doc in other.data:
            val = self._extract_key(doc, key_other)
            hashmap.setdefault(val, []).append(doc)

        result = []
        # Process left side (self)
        matched_right_keys = set()

        for doc_left in self.data:
            val_left = self._extract_key(doc_left, key_self)
            if val_left in hashmap:
                for doc_right in hashmap[val_left]:
                    matched_right_keys.add(id(doc_right))
                    result.append({
                        "left": doc_left,
                        "right": doc_right
                    })
            else:
                if join_type in ("left", "full"):
                    result.append({
                        "left": doc_left,
                        "right": None
                    })

        # Process unmatched right side (right join or full join)
        if join_type in ("right", "full"):
            for doc_right in other.data:
                if id(doc_right) not in matched_right_keys:
                    result.append({
                        "left": None,
                        "right": doc_right
                    })

        return result
    def pipeline(self, query=None, project_fields=None,
                 group_key=None, agg_func=None,
                 join_collection=None, join_self_key=None, 
                 join_other_key=None, join_type="inner"):
        data = self.data

        if query:
            data = Collection(data).find(query)

        if project_fields:
            data = Collection(data).project(project_fields)

        if group_key and agg_func:
            data = Collection(data).aggregate(group_key, agg_func)

        if join_collection:
            data = Collection(data).hash_join(
                join_collection,
                join_self_key,
                join_other_key,
                join_type
            )

        return data

# ============================================================================
# Aggregate Functions (from final_code.ipynb)
# ============================================================================

def agg_count(field=None):
    return lambda docs: len(docs)

def agg_sum(field):
    return lambda docs: sum(
        doc.get(field, 0) for doc in docs
        if isinstance(doc.get(field), (int, float))
    )

def agg_max(field):
    return lambda docs: max(
        doc.get(field) for doc in docs
        if isinstance(doc.get(field), (int, float))
    )

def agg_min(field):
    return lambda docs: min(
        doc.get(field) for doc in docs
        if isinstance(doc.get(field), (int, float))
    )

def agg_avg(field):
    return lambda docs: (
        sum(doc.get(field, 0) for doc in docs
            if isinstance(doc.get(field), (int, float)))
        / len(docs)
        if docs else None
    )

# ============================================================================
# Load JSON/JSONL Files (from final_code.ipynb)
# ============================================================================
def load_json_chunks(path, chunk_size=5000):
    """
    Generic loader:
        - if JSONL:  one JSON object per line
        - if JSON array: [ {...}, {...} ]
    """
    with open(path, "r", encoding="utf-8") as f:
        first_char = f.read(1)#to identify whether it is a josn or a jsonl
        f.seek(0)#go back to the begining 

        if first_char == "[":  # JSON array
            text = f.read()
            parser = Parser()
            arr = parser.parse(text)
            for i in range(0, len(arr), chunk_size):
                yield arr[i:i + chunk_size]
        else: # JSONL
            parser = Parser()
            buffer = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                buffer.append(parser.parse(line))
                if len(buffer) >= chunk_size:
                    yield buffer
                    buffer = []
            if buffer:
                yield buffer

# ============================================================================
# Partial Aggregation (for chunk processing)
# ============================================================================

class PartialAgg:
    """merge of partial aggregation results"""

    @staticmethod
    def merge_count(v1, v2):
        return v1 + v2

    @staticmethod
    def merge_sum(v1, v2):
        return v1 + v2

    @staticmethod
    def merge_max(v1, v2):
        return max(v1, v2)

    @staticmethod
    def merge_min(v1, v2):
        return min(v1, v2)

    @staticmethod
    def merge_avg(avg1, count1, avg2, count2):
        # weighted average
        total = count1 + count2
        return (avg1 * count1 + avg2 * count2) / total, total

def calculate_average_engagement_by_location(filepath, chunk_size=5000):
    """
    Calculates the Average Engagement Rate (AER) grouped by IP location 
    for large datasets using chunked processing and partial aggregation merging.
    This demonstrates the project's scaling requirement.
    AER = (Total Reposts + Total Comments + Total Attitudes) / Total Posts
    """
    
    # 1. initialize four global partial result containers
    # Dictionaries to store merged partial aggregation results globally
    partial_counts = {}
    partial_reposts_sums = {}
    partial_comments_sums = {}
    partial_attitudes_sums = {}
    
    # 2. process the file chunk by chunk
    for chunk in load_json_chunks(filepath, chunk_size):
        coll = Collection(chunk)
    
        # local aggregation calculations (Grouped by "ip_location")
        chunk_counts = coll.aggregate("ip_location", agg_count())
        chunk_reposts = coll.aggregate("ip_location", agg_sum("reposts_count"))
        chunk_comments = coll.aggregate("ip_location", agg_sum("comments_count"))
        chunk_attitudes = coll.aggregate("ip_location", agg_sum("attitudes_count"))
        
        # 3. merge Local Results
        
        # Merge Counts (Total Posts)
        for loc, count in chunk_counts.items():
            current_count = partial_counts.get(loc, 0)
            # use PartialAgg.merge_count to combine current global total with local chunk total
            partial_counts[loc] = PartialAgg.merge_count(current_count, count)
            
        # Merge Reposts Sums
        for loc, total in chunk_reposts.items():
            current_total = partial_reposts_sums.get(loc, 0)
            # Use PartialAgg.merge_sum for addition
            partial_reposts_sums[loc] = PartialAgg.merge_sum(current_total, total)
            
        # Merge Comments Sums
        for loc, total in chunk_comments.items():
            current_total = partial_comments_sums.get(loc, 0)
            partial_comments_sums[loc] = PartialAgg.merge_sum(current_total, total)
            
        # Merge Attitudes (Likes) Sums
        for loc, total in chunk_attitudes.items():
            current_total = partial_attitudes_sums.get(loc, 0)
            partial_attitudes_sums[loc] = PartialAgg.merge_sum(current_total, total)
            
    # 4. Calculate Final Average Engagement Rate (Final Calculation)
    final_results = {}
    for loc in partial_counts:
        # Get all global sums
        total_interactions = (
            partial_reposts_sums.get(loc, 0) +
            partial_comments_sums.get(loc, 0) +
            partial_attitudes_sums.get(loc, 0)
        )
        total_posts = partial_counts[loc]
        
        # Calculate Average Engagement Rate, prevent division by zero
        avg_engagement_rate = total_interactions / total_posts if total_posts else 0
        
        final_results[loc] = {
            "Total_Posts": total_posts,
            "Avg_Engagement_Rate": avg_engagement_rate
        }
    
    return final_results

# ============================================================================
# Streamlit App
# ============================================================================

st.set_page_config(
    page_title="JSON Query System",
    page_icon=None,
    layout="wide"
)

st.title("JSON Query System")
st.markdown("Custom JSON Parser with Query Operations")

# Sidebar for file upload
st.sidebar.header("Data Loading")

uploaded_file = st.sidebar.file_uploader(
    "Upload JSON/JSONL File",
    type=['json', 'jsonl'],
    help="Supports JSON array or JSONL format"
)

# Also allow selecting from existing files
existing_files = []
import os
if os.path.exists("chatgpt 20240514-0914.jsonl"):
    existing_files.append("chatgpt 20240514-0914.jsonl")
if os.path.exists("chatgpt 20240915-1231.jsonl"):
    existing_files.append("chatgpt 20240915-1231.jsonl")

if existing_files:
    selected_file = st.sidebar.selectbox(
        "Or Select Existing File",
        [None] + existing_files
    )
else:
    selected_file = None

# Initialize session state
if 'collection' not in st.session_state:
    st.session_state.collection = None
if 'collection_b' not in st.session_state:
    st.session_state.collection_b = None
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'join_results' not in st.session_state:
    st.session_state.join_results = None
if 'use_join_results' not in st.session_state:
    st.session_state.use_join_results = False
if 'current_file_name' not in st.session_state:
    st.session_state.current_file_name = None

# Load data
if uploaded_file is not None:
    # Check if this is a new file
    new_file_name = uploaded_file.name
    file_changed = st.session_state.current_file_name != new_file_name
    
    with st.spinner("Loading data..."):
        try:
            # Save uploaded file temporarily
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            data = load_json_file(temp_path)
            st.session_state.collection = Collection(data)
            st.session_state.data_loaded = True
            st.session_state.current_file_name = new_file_name
            
            # Clear join results when new file is loaded
            if file_changed:
                st.session_state.join_results = None
                st.session_state.use_join_results = False
                st.session_state.collection_b = None
            
            st.sidebar.success(f"Loaded {len(data)} records")
            
            # Clean up temp file
            os.remove(temp_path)
        except Exception as e:
            st.sidebar.error(f"Load failed: {str(e)}")
            st.session_state.data_loaded = False

elif selected_file is not None:
    # Check if this is a new file
    file_changed = st.session_state.current_file_name != selected_file
    
    with st.spinner("Loading data..."):
        try:
            data = load_json_file(selected_file)
            st.session_state.collection = Collection(data)
            st.session_state.data_loaded = True
            st.session_state.current_file_name = selected_file
            
            # Clear join results when new file is loaded
            if file_changed:
                st.session_state.join_results = None
                st.session_state.use_join_results = False
                st.session_state.collection_b = None
            
            st.sidebar.success(f"Loaded {len(data)} records")
        except Exception as e:
            st.sidebar.error(f"Load failed: {str(e)}")
            st.session_state.data_loaded = False

# Main content area
if not st.session_state.data_loaded or st.session_state.collection is None:
    st.info("Upload or select a data file to begin")
else:
    # Tabs for different operations
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Find", 
        "Project", 
        "Aggregate",
        "Join",
        "Analysis"
    ])
    
    # Determine which collection to use
    if st.session_state.use_join_results and st.session_state.join_results:
        # Use join results as the working collection
        # Join results have structure: [{"left": {...}, "right": {...}}, ...]
        # We need to flatten this for easier field access
        flattened_join_results = []
        for r in st.session_state.join_results:
            flat = {}
            if r.get("left"):
                for k, v in r["left"].items():
                    flat[f"left.{k}"] = v
            if r.get("right"):
                for k, v in r["right"].items():
                    flat[f"right.{k}"] = v
            flattened_join_results.append(flat)
        working_collection = Collection(flattened_join_results)
    else:
        working_collection = st.session_state.collection
    
    collection = working_collection
    
    # Get available fields from data - always recalculate from current collection
    if collection and collection.data:
        available_fields = get_all_fields(collection.data)
    else:
        available_fields = []
    
    # Create a unique key suffix based on current file to force widget reset
    file_key_suffix = st.session_state.current_file_name or "default"
    
    # Tab 1: Find
    with tab1:
        st.header("Find")
        if st.session_state.use_join_results:
            st.info("Working with Join results")
        st.caption("Filter documents by field-value equality")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if available_fields:
                # Find index for default field
                default_idx = 0
                if "ip_location" in available_fields:
                    default_idx = available_fields.index("ip_location") + 1
                
                query_key = st.selectbox("Field", options=[""] + available_fields, index=default_idx, help="Select a field to query", key=f"find_field_{file_key_suffix}")
                
                if query_key:
                    # Use text input for value - user can enter any value directly
                    query_value = st.text_input("Value", value="", help="Enter value to match (case-insensitive for strings)", key=f"find_value_{file_key_suffix}")
                else:
                    query_value = st.text_input("Value", value="", disabled=True, key=f"find_value_disabled_{file_key_suffix}")
            else:
                query_key = st.text_input("Field", value="", help="Enter field name", key=f"find_field_text_{file_key_suffix}")
                query_value = st.text_input("Value", value="", key=f"find_value_text_manual_{file_key_suffix}")
        
        with col2:
            st.caption("Available Fields")
            if available_fields:
                st.code("\n".join(available_fields[:15]), language=None)
                if len(available_fields) > 15:
                    st.caption(f"... and {len(available_fields) - 15} more")
            else:
                st.caption("No fields detected")
        
        if st.button("Execute", type="primary", key="find_execute"):
            try:
                if not query_key or not query_value:
                    st.warning("Please select both field and value")
                else:
                    query = {query_key: query_value}
                    results = collection.find(query)
                
                    st.caption(f"{len(results)} records found")
                    
                    if results:
                        num_preview = st.slider("Preview", 1, min(10, len(results)), 5)
                        
                        for i, doc in enumerate(results[:num_preview]):
                            with st.expander(f"Record {i+1}"):
                                st.json(doc)
                        
                        st.download_button(
                            label="Download JSON",
                            data=json.dumps(results, ensure_ascii=False, indent=2),
                            file_name="query_results.json",
                            mime="application/json"
                        )
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Tab 2: Project
    with tab2:
        st.header("Project")
        if st.session_state.use_join_results:
            st.info("Working with Join results")
        st.caption("Select fields to display")
        
        if available_fields:
            selected_fields = st.multiselect(
                "Fields",
                options=available_fields,
                default=[],
                help="Select one or more fields to display",
                key=f"project_fields_{file_key_suffix}"
            )
            fields_input = ", ".join(selected_fields) if selected_fields else ""
            
            # Also allow manual input for custom fields
            with st.expander("Add Custom Field"):
                custom_field = st.text_input("Custom Field", value="", help="Add a field not in the list", key=f"project_custom_{file_key_suffix}")
                if custom_field:
                    if custom_field not in selected_fields:
                        selected_fields.append(custom_field)
                        fields_input = ", ".join(selected_fields)
        else:
            fields_input = st.text_input(
                "Fields",
                value="",
                help="Comma-separated list. Supports dot notation for nested fields.",
                key=f"project_fields_text_{file_key_suffix}"
            )
        
        if st.button("Execute", type="primary", key="project_execute"):
            try:
                if available_fields and selected_fields:
                    fields = selected_fields
                else:
                    fields = [f.strip() for f in fields_input.split(",") if f.strip()]
                
                if not fields:
                    st.warning("At least one field required")
                else:
                    results = collection.project(fields)
                    
                    st.caption(f"{len(results)} records")
                    
                    if results:
                        df = pd.DataFrame(results)
                        st.dataframe(df, use_container_width=True)
                        
                        st.download_button(
                            label="Download CSV",
                            data=df.to_csv(index=False).encode('utf-8'),
                            file_name="projected_results.csv",
                            mime="text/csv"
                        )
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Tab 3: Aggregate
    with tab3:
        st.header("Aggregate")
        if st.session_state.use_join_results:
            st.info("Working with Join results")
        st.caption("Group by field and apply aggregation function")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if available_fields:
                group_key = st.selectbox("Group By", options=[""] + available_fields, index=0, help="Select field to group by", key=f"agg_group_{file_key_suffix}")
            else:
                group_key = st.text_input("Group By", value="", key=f"agg_group_text_{file_key_suffix}")
            
            agg_type = st.selectbox(
                "Function",
                ["count", "sum", "avg", "max", "min"],
                key=f"agg_type_{file_key_suffix}"
            )
        
        with col2:
            if agg_type != "count":
                if available_fields:
                    agg_field = st.selectbox("Field", options=[""] + available_fields, index=0, help="Select field to aggregate", key=f"agg_field_{file_key_suffix}")
                else:
                    agg_field = st.text_input("Field", value="", key=f"agg_field_text_{file_key_suffix}")
            else:
                agg_field = None
                st.caption("Count does not require a field")
        
        if st.button("Execute", type="primary", key="aggregate_execute"):
            try:
                if not group_key:
                    st.warning("Please select a group field")
                elif agg_type != "count" and not agg_field:
                    st.warning("Please select an aggregation field")
                else:
                    if agg_type == "count":
                        agg_func = agg_count()
                    elif agg_type == "sum":
                        agg_func = agg_sum(agg_field)
                    elif agg_type == "avg":
                        agg_func = agg_avg(agg_field)
                    elif agg_type == "max":
                        agg_func = agg_max(agg_field)
                    elif agg_type == "min":
                        agg_func = agg_min(agg_field)
                    
                    results = collection.aggregate(group_key, agg_func)
                
                    st.caption(f"{len(results)} groups")
                    
                    df = pd.DataFrame([
                        {"Group": k, "Value": v}
                        for k, v in results.items()
                    ])
                    df = df.sort_values("Value", ascending=False)
                    
                    st.dataframe(df, use_container_width=True)
                    
                    chart_type = st.selectbox("Chart", ["Bar", "Pie"], key="agg_chart")
                    
                    if chart_type == "Bar":
                        st.bar_chart(df.set_index("Group"))
                    else:
                        pie_df = df.head(10)
                        fig = px.pie(pie_df, values='Value', names='Group')
                        st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Tab 4: Join
    with tab4:
        st.header("Join")
        st.caption("Hash join operation on two datasets")
        
        uploaded_file_b = st.file_uploader(
            "Second Dataset",
            type=['json', 'jsonl'],
            key="join_file"
        )
        
        if uploaded_file_b is not None:
            with st.spinner("Loading..."):
                try:
                    temp_path = f"temp_join_{uploaded_file_b.name}"
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file_b.getbuffer())
                    
                    data_b = load_json_file(temp_path)
                    st.session_state.collection_b = Collection(data_b)
                    st.caption(f"Loaded {len(data_b)} records")
                    os.remove(temp_path)
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        if st.session_state.collection_b is not None:
            # Get fields from both collections
            fields_b = get_all_fields(st.session_state.collection_b.data) if st.session_state.collection_b.data else []
            all_join_fields = sorted(set(available_fields + fields_b))
            
            col1, col2 = st.columns(2)
            
            with col1:
                if all_join_fields:
                    key_self = st.selectbox("Left Key", options=[""] + available_fields, index=0 if "user._id" in available_fields else 0, help="Field from first dataset", key=f"join_left_{file_key_suffix}")
                    key_other = st.selectbox("Right Key", options=[""] + fields_b, index=0 if "user._id" in fields_b else 0, help="Field from second dataset", key=f"join_right_{file_key_suffix}")
                else:
                    key_self = st.text_input("Left Key", value="", key=f"join_left_text_{file_key_suffix}")
                    key_other = st.text_input("Right Key", value="", key=f"join_right_text_{file_key_suffix}")
            
            with col2:
                join_type = st.selectbox("Type", ["inner", "left", "right", "full"], key=f"join_type_{file_key_suffix}")
            
            if st.button("Execute", type="primary", key="join_execute"):
                try:
                    if not key_self or not key_other:
                        st.warning("Please select both join keys")
                    else:
                        results = collection.hash_join(
                            st.session_state.collection_b,
                            key_self,
                            key_other,
                            join_type
                        )
                        
                        # Save results to session state for use in other tabs
                        st.session_state.join_results = results
                        st.session_state.use_join_results = True
                    
                        st.success(f"Join completed: {len(results)} records")
                        st.caption("Results saved. You can now use them in other tabs (Find, Project, Aggregate)")
                        
                        num_preview = st.slider("Preview", 1, min(5, len(results)), 3, key="join_preview")
                        
                        for i, result in enumerate(results[:num_preview]):
                            with st.expander(f"Record {i+1}"):
                                st.json(result)
                        
                        # Export options
                        st.subheader("Export Results")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.download_button(
                                label="Download JSON",
                                data=json.dumps(results, ensure_ascii=False, indent=2),
                                file_name="join_results.json",
                                mime="application/json",
                                key="join_download_json"
                            )
                        
                        with col2:
                            # Convert to flattened format for CSV
                            flattened_results = []
                            for r in results:
                                flat = {}
                                if r.get("left"):
                                    for k, v in r["left"].items():
                                        flat[f"left.{k}"] = v
                                if r.get("right"):
                                    for k, v in r["right"].items():
                                        flat[f"right.{k}"] = v
                                flattened_results.append(flat)
                            
                            if flattened_results:
                                df_join = pd.DataFrame(flattened_results)
                                st.download_button(
                                    label="Download CSV",
                                    data=df_join.to_csv(index=False).encode('utf-8'),
                                    file_name="join_results.csv",
                                    mime="text/csv",
                                    key="join_download_csv"
                                )
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            
            # Show option to clear join results
            if st.session_state.join_results is not None:
                st.markdown("---")
                if st.button("Clear Join Results", key="clear_join"):
                    st.session_state.join_results = None
                    st.session_state.use_join_results = False
                    st.success("Join results cleared")
                    st.rerun()
        else:
            st.caption("Upload second dataset to proceed")
    
    # Tab 5: Analysis
    with tab5:
        st.header("Analysis")
        st.caption("Dataset inspection and statistics")
        
        analysis_type = st.selectbox(
            "Mode",
            ["Overview", "Field Statistics", "Engagement by Location"],
            key=f"analysis_type_{file_key_suffix}"
        )
        
        if analysis_type == "Overview":
            sample_doc = collection.data[0] if collection.data else {}
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Records", len(collection.data))
            col2.metric("Fields", len(sample_doc))
            col3.metric("Type", "JSON")
            
            st.subheader("Schema")
            st.json(sample_doc)
            
            if sample_doc:
                def get_all_keys(obj, prefix=""):
                    keys = []
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            full_key = f"{prefix}.{k}" if prefix else k
                            keys.append(full_key)
                            if isinstance(v, (dict, list)):
                                keys.extend(get_all_keys(v, full_key))
                    elif isinstance(obj, list) and obj:
                        keys.extend(get_all_keys(obj[0], prefix))
                    return keys
                
                all_keys = get_all_keys(sample_doc)
                st.caption("Available Fields")
                st.code("\n".join(sorted(set(all_keys))[:20]))
        
        elif analysis_type == "Field Statistics":
            if available_fields:
                field_to_analyze = st.selectbox("Field", options=[""] + available_fields, index=0 if "ip_location" in available_fields else 0, key=f"analyze_field_{file_key_suffix}")
            else:
                field_to_analyze = st.text_input("Field", value="", key=f"analyze_field_text_{file_key_suffix}")
            
            if st.button("Analyze", type="primary", key="analyze_execute"):
                try:
                    if not field_to_analyze:
                        st.warning("Please select a field")
                    else:
                        counts = collection.aggregate(field_to_analyze, agg_count())
                    
                        df = pd.DataFrame([
                            {"Value": k, "Count": v}
                            for k, v in counts.items()
                        ]).sort_values("Count", ascending=False)
                        
                        st.dataframe(df.head(20), use_container_width=True)
                        st.bar_chart(df.head(10).set_index("Value"))
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        elif analysis_type == "Engagement by Location":
            st.subheader("Average Engagement Rate by Location")
            st.caption("Calculate AER using chunk processing: (Reposts + Comments + Attitudes) / Posts")
            
            col1, col2 = st.columns(2)
            with col1:
                chunk_size = st.number_input("Chunk Size", min_value=100, max_value=50000, value=5000, step=100, help="Number of records per chunk")
            
            with col2:
                st.caption("Uses chunk processing for large files")
                st.caption("Processes file in chunks and merges partial results")
            
            # Get file path from session state or allow upload
            file_to_process = None
            temp_file_created = False
            
            if st.session_state.data_loaded and st.session_state.collection:
                use_current = st.checkbox("Use currently loaded data", value=True)
                if use_current:
                    # Save current data to temp file for processing
                    import tempfile
                    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8')
                    for doc in st.session_state.collection.data:
                        temp_file.write(json.dumps(doc, ensure_ascii=False) + '\n')
                    temp_file.close()
                    file_to_process = temp_file.name
                    temp_file_created = True
                else:
                    uploaded_analysis_file = st.file_uploader("Or upload a file", type=['json', 'jsonl'], key="engagement_file")
                    if uploaded_analysis_file:
                        temp_path = f"temp_engagement_{uploaded_analysis_file.name}"
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_analysis_file.getbuffer())
                        file_to_process = temp_path
            else:
                uploaded_analysis_file = st.file_uploader("Upload a file", type=['json', 'jsonl'], key="engagement_file")
                if uploaded_analysis_file:
                    temp_path = f"temp_engagement_{uploaded_analysis_file.name}"
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_analysis_file.getbuffer())
                    file_to_process = temp_path
            
            if file_to_process and st.button("Calculate", type="primary", key="engagement_calculate"):
                try:
                    with st.spinner("Processing chunks..."):
                        results = calculate_average_engagement_by_location(file_to_process, chunk_size)
                    
                    if results:
                        # Convert to DataFrame
                        df = pd.DataFrame([
                            {
                                "Location": loc,
                                "Total Posts": data["Total_Posts"],
                                "Avg Engagement Rate": round(data["Avg_Engagement_Rate"], 2)
                            }
                            for loc, data in results.items()
                        ]).sort_values("Avg Engagement Rate", ascending=False)
                        
                        st.success(f"Processed {sum(data['Total_Posts'] for data in results.values())} total posts across {len(results)} locations")
                        
                        st.dataframe(df, use_container_width=True)
                        
                        # Visualization
                        st.subheader("Visualization")
                        chart_type = st.selectbox("Chart Type", ["Bar Chart", "Table"], key="engagement_chart")
                        
                        if chart_type == "Bar Chart":
                            top_n = st.slider("Top N Locations", 5, min(20, len(df)), 10, key="engagement_topn")
                            chart_df = df.head(top_n)
                            st.bar_chart(chart_df.set_index("Location")["Avg Engagement Rate"])
                        
                        # Download results
                        st.download_button(
                            label="Download Results (CSV)",
                            data=df.to_csv(index=False).encode('utf-8'),
                            file_name="engagement_by_location.csv",
                            mime="text/csv"
                        )
                    
                    # Cleanup temp file if created
                    if temp_file_created and os.path.exists(file_to_process):
                        os.unlink(file_to_process)
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
            elif not file_to_process:
                st.info("Please load data first or upload a file")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### Operations")
st.sidebar.markdown("""
- **Find**: Filter by field-value equality
- **Project**: Select fields to display
- **Aggregate**: Group and apply functions
- **Join**: Hash join two datasets
- **Analysis**: Schema and statistics
""")

