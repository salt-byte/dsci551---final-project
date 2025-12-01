# Streamlit 应用详细代码解析

## 概述

这段代码实现了一个基于 Streamlit 的 Web 应用界面，用于交互式查询和分析 JSON/JSONL 数据。它集成了之前实现的所有核心功能（自定义 JSON 解析器、Collection 类、聚合函数等），提供了一个友好的图形界面。

---

## 1. 页面配置和初始化（470-481 行）

### 1.1 页面配置

```python
st.set_page_config(
    page_title="JSON Query System",
    page_icon=None,
    layout="wide"
)
```

**详细解析**：

- **`st.set_page_config()`**：设置 Streamlit 页面的全局配置
  - **`page_title`**：浏览器标签页显示的标题
  - **`page_icon`**：页面图标（这里设为 `None`，表示无图标）
  - **`layout="wide"`**：使用宽屏布局（而不是默认的居中布局）
    - 宽屏布局充分利用屏幕宽度，适合数据表格展示

### 1.2 页面标题

```python
st.title("JSON Query System")
st.markdown("Custom JSON Parser with Query Operations")
```

- **`st.title()`**：显示大标题（H1 级别）
- **`st.markdown()`**：显示 Markdown 格式的副标题

---

## 2. 侧边栏：文件加载（483-506 行）

### 2.1 侧边栏标题

```python
st.sidebar.header("Data Loading")
```

- **`st.sidebar`**：访问侧边栏组件
- **`header()`**：显示侧边栏的标题

### 2.2 文件上传组件

```python
uploaded_file = st.sidebar.file_uploader(
    "Upload JSON/JSONL File",
    type=['json', 'jsonl'],
    help="Supports JSON array or JSONL format"
)
```

**详细解析**：

- **`st.file_uploader()`**：创建文件上传组件
  - **第一个参数**：组件标签文本
  - **`type=['json', 'jsonl']`**：限制只能上传 JSON 和 JSONL 文件
  - **`help`**：鼠标悬停显示的提示信息
  - **返回值**：如果文件已上传，返回 `UploadedFile` 对象；否则返回 `None`

**文件对象特点**：
- `uploaded_file.name`：文件名
- `uploaded_file.getbuffer()`：文件的二进制内容
- 可以像文件对象一样读取

### 2.3 选择现有文件

```python
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
```

**详细解析**：

1. **检查文件是否存在**：
   - 使用 `os.path.exists()` 检查特定文件是否存在
   - 这里硬编码了两个示例文件名

2. **创建选择框**：
   - **`st.selectbox()`**：创建下拉选择框
   - **选项列表**：`[None] + existing_files`
     - `None` 表示"不选择"选项（放在第一位）
     - 后面跟存在的文件列表
   - 如果文件存在，显示选择框；否则 `selected_file = None`

**设计思路**：
- 提供两种加载方式：上传新文件 或 选择已有文件
- 方便快速切换不同的数据集

---

## 3. Session State 初始化（508-520 行）

```python
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
```

**Session State 是什么**：

- Streamlit 的特殊机制，用于在页面刷新之间保持数据
- 每次用户交互（点击按钮、选择下拉框等），页面会重新运行脚本
- 如果没有 Session State，所有变量都会重置
- Session State 可以"记住"之前的状态

**每个变量的作用**：

1. **`collection`**：
   - 主数据集的 Collection 对象
   - 初始值：`None`

2. **`collection_b`**：
   - 第二个数据集（用于 Join 操作）
   - 初始值：`None`

3. **`data_loaded`**：
   - 布尔标志，表示数据是否已加载
   - 初始值：`False`

4. **`join_results`**：
   - 存储 Join 操作的结果
   - 初始值：`None`

5. **`use_join_results`**：
   - 布尔标志，表示是否使用 Join 结果作为工作数据集
   - 初始值：`False`

6. **`current_file_name`**：
   - 当前加载的文件名
   - 用于检测文件是否变化

**为什么使用这种模式**：

```python
if 'collection' not in st.session_state:
    st.session_state.collection = None
```

- 检查变量是否已存在
- 如果不存在（第一次运行），才初始化
- 如果已存在（页面刷新后），保留原值
- 避免覆盖已有的数据

---

## 4. 数据加载逻辑（522-574 行）

### 4.1 处理上传的文件

```python
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
```

**详细流程解析**：

#### 步骤 1：检查是否上传了新文件

```python
new_file_name = uploaded_file.name
file_changed = st.session_state.current_file_name != new_file_name
```

- 获取上传文件的名称
- 比较是否与当前文件名不同
- 如果不同，说明用户上传了新文件

#### 步骤 2：显示加载动画

```python
with st.spinner("Loading data..."):
    # 加载过程
```

- **`st.spinner()`**：显示加载动画（转圈图标）
- 在 `with` 块内的代码执行时显示，完成后自动消失

#### 步骤 3：保存临时文件

```python
temp_path = f"temp_{uploaded_file.name}"
with open(temp_path, "wb") as f:
    f.write(uploaded_file.getbuffer())
```

**为什么需要临时文件**：
- `load_json_file()` 函数需要文件路径，而不是文件对象
- 上传的文件在内存中，需要先写入磁盘

**文件命名**：
- `temp_` + 原文件名
- 例如：`temp_data.jsonl`

**`getbuffer()`**：
- 获取文件的二进制内容
- 可以直接写入文件

#### 步骤 4：加载和解析数据

```python
data = load_json_file(temp_path)
st.session_state.collection = Collection(data)
st.session_state.data_loaded = True
st.session_state.current_file_name = new_file_name
```

1. **`load_json_file()`**：使用自定义解析器加载 JSON/JSONL 文件
2. **创建 Collection**：包装数据，提供查询 API
3. **更新状态**：
   - `data_loaded = True`：标记数据已加载
   - `current_file_name`：记录当前文件名

#### 步骤 5：清除 Join 结果（如果文件变化）

```python
if file_changed:
    st.session_state.join_results = None
    st.session_state.use_join_results = False
    st.session_state.collection_b = None
```

**逻辑**：
- 如果上传了新文件，之前的 Join 结果不再有效
- 清除所有 Join 相关状态
- 防止使用错误的数据

#### 步骤 6：显示成功消息

```python
st.sidebar.success(f"Loaded {len(data)} records")
```

- **`st.success()`**：显示绿色成功消息框
- 显示加载的记录数

#### 步骤 7：清理临时文件

```python
os.remove(temp_path)
```

- 删除临时文件，释放磁盘空间

#### 异常处理

```python
except Exception as e:
    st.sidebar.error(f"Load failed: {str(e)}")
    st.session_state.data_loaded = False
```

- **`st.error()`**：显示红色错误消息框
- 显示错误信息
- 重置 `data_loaded` 标志

---

### 4.2 处理选择的现有文件

```python
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
```

**与上传文件的区别**：
- 不需要创建临时文件（文件已经在磁盘上）
- 直接使用 `selected_file` 路径
- 其他逻辑完全相同

---

## 5. 主界面：标签页和数据处理（576-618 行）

### 5.1 检查数据是否加载

```python
if not st.session_state.data_loaded or st.session_state.collection is None:
    st.info("Upload or select a data file to begin")
else:
    # 主界面内容
```

**逻辑**：
- 如果数据未加载或 Collection 为空，显示提示信息
- 否则，显示主界面

**`st.info()`**：显示蓝色信息框

---

### 5.2 创建标签页

```python
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Find", 
    "Project", 
    "Aggregate",
    "Join",
    "Analysis"
])
```

**详细解析**：

- **`st.tabs()`**：创建标签页组件
  - 参数：标签名称列表
  - 返回值：多个标签页对象（按顺序返回）
  - 每个标签页用 `with tab1:` 语法进入

**标签页功能**：
1. **Find**：查询过滤
2. **Project**：字段投影
3. **Aggregate**：聚合统计
4. **Join**：数据连接
5. **Analysis**：数据分析

---

### 5.3 确定工作数据集

```python
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
```

**详细解析**：

#### 问题：Join 结果的结构

Join 操作返回的结果格式：
```python
[
    {"left": {...}, "right": {...}},
    {"left": {...}, "right": {...}},
    ...
]
```

但在其他操作（Find、Project 等）中，我们需要直接访问字段，而不是通过 `left.field_name` 的方式。

#### 解决方案：扁平化

```python
flattened_join_results = []
for r in st.session_state.join_results:
    flat = {}
    if r.get("left"):
        for k, v in r["left"].items():
            flat[f"left.{k}"] = v  # 添加 "left." 前缀
    if r.get("right"):
        for k, v in r["right"].items():
            flat[f"right.{k}"] = v  # 添加 "right." 前缀
    flattened_join_results.append(flat)
```

**转换示例**：

原始 Join 结果：
```python
{
    "left": {"name": "John", "age": 30},
    "right": {"city": "NYC", "salary": 50000}
}
```

扁平化后：
```python
{
    "left.name": "John",
    "left.age": 30,
    "right.city": "NYC",
    "right.salary": 50000
}
```

**优势**：
- 可以直接使用点号表示法访问字段
- 例如：`"left.name"`、`"right.city"`
- 与其他操作的接口一致

---

### 5.4 提取可用字段

```python
# Get available fields from data - always recalculate from current collection
if collection and collection.data:
    available_fields = get_all_fields(collection.data)
else:
    available_fields = []
```

**详细解析**：

- **`get_all_fields()`**：从数据中提取所有字段路径
  - 支持嵌套字段
  - 返回字段列表，例如：`["name", "age", "user.name", "user.address.city"]`

**为什么要重新计算**：
- 当使用 Join 结果时，字段会变化（增加了 `left.*` 和 `right.*`）
- 每次都要根据当前数据集重新提取字段

**用途**：
- 在 UI 中显示字段下拉列表
- 用户不需要记住字段名，可以直接选择

---

### 5.5 文件键后缀

```python
# Create a unique key suffix based on current file to force widget reset
file_key_suffix = st.session_state.current_file_name or "default"
```

**详细解析**：

**问题**：Streamlit 的组件状态保持

- Streamlit 使用 `key` 参数来识别组件
- 如果 `key` 相同，组件的值会在页面刷新后保留
- 但当我们切换文件时，我们希望组件重置

**解决方案**：

- 将文件名加入 `key` 中
- 当文件名改变时，`key` 也会改变
- Streamlit 会认为这是新组件，自动重置

**使用示例**：
```python
query_key = st.selectbox(
    "Field",
    options=available_fields,
    key=f"find_field_{file_key_suffix}"  # 文件名变化时，key 也变化
)
```

---

## 6. Tab 1: Find（查询）操作（619-679 行）

### 6.1 标签页头部

```python
with tab1:
    st.header("Find")
    if st.session_state.use_join_results:
        st.info("Working with Join results")
    st.caption("Filter documents by field-value equality")
```

- **`st.header()`**：显示标题
- **条件提示**：如果使用 Join 结果，显示提示信息
- **`st.caption()`**：显示小字说明

---

### 6.2 两列布局

```python
col1, col2 = st.columns([2, 1])

with col1:
    # 左侧：查询输入（占 2/3 宽度）
    
with col2:
    # 右侧：可用字段列表（占 1/3 宽度）
```

**`st.columns()`**：
- 创建列布局
- 参数：每列的宽度比例 `[2, 1]` 表示 2:1 的比例

---

### 6.3 字段选择（左侧）

```python
with col1:
    if available_fields:
        # Find index for default field
        default_idx = 0
        if "ip_location" in available_fields:
            default_idx = available_fields.index("ip_location") + 1
        
        query_key = st.selectbox(
            "Field",
            options=[""] + available_fields,
            index=default_idx,
            help="Select a field to query",
            key=f"find_field_{file_key_suffix}"
        )
        
        if query_key:
            query_value = st.text_input(
                "Value",
                value="",
                help="Enter value to match (case-insensitive for strings)",
                key=f"find_value_{file_key_suffix}"
            )
        else:
            query_value = st.text_input(
                "Value",
                value="",
                disabled=True,
                key=f"find_value_disabled_{file_key_suffix}"
            )
    else:
        query_key = st.text_input(
            "Field",
            value="",
            help="Enter field name",
            key=f"find_field_text_{file_key_suffix}"
        )
        query_value = st.text_input(
            "Value",
            value="",
            key=f"find_value_text_manual_{file_key_suffix}"
        )
```

**详细解析**：

#### 情况 1：有可用字段（推荐方式）

1. **设置默认字段**：
   ```python
   default_idx = 0
   if "ip_location" in available_fields:
       default_idx = available_fields.index("ip_location") + 1
   ```
   - 默认选择第一个字段（`index=0` 是空字符串）
   - 如果存在 `ip_location`，默认选择它（`+1` 因为第一个是空字符串）

2. **字段选择框**：
   ```python
   query_key = st.selectbox(
       "Field",
       options=[""] + available_fields,  # 第一个选项是空字符串
       index=default_idx,
       key=f"find_field_{file_key_suffix}"
   )
   ```
   - **下拉框**：用户从列表中选择字段
   - **第一个选项为空**：表示"未选择"
   - **使用文件键后缀**：切换文件时自动重置

3. **值输入框**：
   - 如果字段已选择：启用输入框
   - 如果字段未选择：禁用输入框（`disabled=True`）

#### 情况 2：无可用字段（手动输入）

- 提供文本输入框，用户可以手动输入字段名
- 适用于字段提取失败的情况

---

### 6.4 可用字段列表（右侧）

```python
with col2:
    st.caption("Available Fields")
    if available_fields:
        st.code("\n".join(available_fields[:15]), language=None)
        if len(available_fields) > 15:
            st.caption(f"... and {len(available_fields) - 15} more")
    else:
        st.caption("No fields detected")
```

**详细解析**：

- **`st.code()`**：以代码格式显示文本（等宽字体）
- **只显示前 15 个字段**：避免列表过长
- **如果超过 15 个**：显示省略提示

---

### 6.5 执行查询

```python
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
```

**详细流程**：

#### 步骤 1：创建按钮

```python
st.button("Execute", type="primary", key="find_execute")
```

- **`type="primary"`**：主按钮样式（蓝色高亮）
- 点击按钮时，返回 `True`，触发后续代码

#### 步骤 2：验证输入

```python
if not query_key or not query_value:
    st.warning("Please select both field and value")
```

- **`st.warning()`**：显示黄色警告框
- 确保用户输入了字段和值

#### 步骤 3：执行查询

```python
query = {query_key: query_value}
results = collection.find(query)
```

- 构建查询字典
- 调用 Collection 的 `find()` 方法

#### 步骤 4：显示结果数量

```python
st.caption(f"{len(results)} records found")
```

#### 步骤 5：可调整的预览

```python
num_preview = st.slider("Preview", 1, min(10, len(results)), 5)
```

- **`st.slider()`**：创建滑块组件
- 参数：
  - 标签："Preview"
  - 最小值：1
  - 最大值：`min(10, len(results))`（最多 10 条，或结果数量）
  - 默认值：5
- 用户可以通过滑块选择预览多少条记录

#### 步骤 6：展开式预览

```python
for i, doc in enumerate(results[:num_preview]):
    with st.expander(f"Record {i+1}"):
        st.json(doc)
```

- **`st.expander()`**：创建可展开的容器
  - 默认收起，点击后展开
  - 适合展示多条记录
- **`st.json()`**：以 JSON 格式美观显示数据
  - 自动格式化
  - 可折叠嵌套结构

#### 步骤 7：下载结果

```python
st.download_button(
    label="Download JSON",
    data=json.dumps(results, ensure_ascii=False, indent=2),
    file_name="query_results.json",
    mime="application/json"
)
```

- **`st.download_button()`**：创建下载按钮
  - **`data`**：要下载的数据（字符串或字节）
  - **`file_name`**：下载的文件名
  - **`mime`**：文件类型
- **`json.dumps()`**：将 Python 对象转换为 JSON 字符串
  - **`ensure_ascii=False`**：允许非 ASCII 字符（中文等）
  - **`indent=2`**：格式化缩进（2 个空格）

---

## 7. Tab 2: Project（投影）操作（681-738 行）

### 7.1 多选字段

```python
if available_fields:
    selected_fields = st.multiselect(
        "Fields",
        options=available_fields,
        default=[],
        help="Select one or more fields to display",
        key=f"project_fields_{file_key_suffix}"
    )
```

**详细解析**：

- **`st.multiselect()`**：创建多选下拉框
  - 用户可以按住 Ctrl/Cmd 选择多个字段
  - **`default=[]`**：默认不选择任何字段
  - 返回选择的字段列表

---

### 7.2 自定义字段

```python
# Also allow manual input for custom fields
with st.expander("Add Custom Field"):
    custom_field = st.text_input(
        "Custom Field",
        value="",
        help="Add a field not in the list",
        key=f"project_custom_{file_key_suffix}"
    )
    if custom_field:
        if custom_field not in selected_fields:
            selected_fields.append(custom_field)
            fields_input = ", ".join(selected_fields)
```

**详细解析**：

- **可展开区域**：默认收起，用户可以展开输入自定义字段
- **添加到列表**：如果输入了自定义字段，且不在已选列表中，则添加
- 支持点号表示法的嵌套字段

---

### 7.3 执行投影

```python
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
```

**详细解析**：

#### 字段处理

```python
if available_fields and selected_fields:
    fields = selected_fields  # 使用多选列表
else:
    fields = [f.strip() for f in fields_input.split(",") if f.strip()]  # 手动输入
```

- 如果有字段列表且已选择，使用选择的字段
- 否则，从文本输入解析（逗号分隔）

#### 转换为 DataFrame

```python
df = pd.DataFrame(results)
st.dataframe(df, use_container_width=True)
```

- **`pd.DataFrame()`**：将字典列表转换为 Pandas DataFrame
- **`st.dataframe()`**：显示交互式数据表格
  - **`use_container_width=True`**：使用全宽显示
  - 支持排序、搜索等功能

#### 下载 CSV

```python
df.to_csv(index=False).encode('utf-8')
```

- **`to_csv(index=False)`**：转换为 CSV 字符串（不包含索引）
- **`.encode('utf-8')`**：编码为字节（下载需要）

---

## 8. Tab 3: Aggregate（聚合）操作（740-810 行）

### 8.1 分组字段和聚合函数

```python
col1, col2 = st.columns(2)

with col1:
    group_key = st.selectbox("Group By", ...)
    agg_type = st.selectbox("Function", ["count", "sum", "avg", "max", "min"])

with col2:
    if agg_type != "count":
        agg_field = st.selectbox("Field", ...)
    else:
        agg_field = None
        st.caption("Count does not require a field")
```

**详细解析**：

- **两列布局**：左侧选择分组和函数，右侧选择聚合字段
- **条件显示**：
  - 如果选择 `count`，不需要聚合字段（统计数量）
  - 其他函数需要选择要聚合的字段

---

### 8.2 执行聚合

```python
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
```

**详细解析**：

- 根据用户选择创建对应的聚合函数
- 调用 Collection 的 `aggregate()` 方法

---

### 8.3 可视化

```python
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
```

**详细解析**：

#### 创建结果表格

```python
df = pd.DataFrame([
    {"Group": k, "Value": v}
    for k, v in results.items()
])
```

- 将字典结果转换为 DataFrame
- 两列：Group（分组值）、Value（聚合值）

#### 排序

```python
df = df.sort_values("Value", ascending=False)
```

- 按聚合值降序排序（最大的在前）

#### 选择图表类型

- **条形图**：`st.bar_chart()`（Streamlit 内置）
- **饼图**：使用 Plotly（`px.pie()`）
  - 只显示前 10 条（避免饼图太复杂）

---

## 9. Tab 4: Join（连接）操作（812-928 行）

### 9.1 加载第二个数据集

```python
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
```

**详细解析**：

- 与主数据集加载逻辑相同
- 保存到 `st.session_state.collection_b`
- 使用不同的临时文件前缀（`temp_join_`）避免冲突

---

### 9.2 Join 配置

```python
if st.session_state.collection_b is not None:
    # Get fields from both collections
    fields_b = get_all_fields(st.session_state.collection_b.data)
    all_join_fields = sorted(set(available_fields + fields_b))
    
    col1, col2 = st.columns(2)
    
    with col1:
        key_self = st.selectbox("Left Key", options=[""] + available_fields, ...)
        key_other = st.selectbox("Right Key", options=[""] + fields_b, ...)
    
    with col2:
        join_type = st.selectbox("Type", ["inner", "left", "right", "full"])
```

**详细解析**：

- **获取两个数据集的字段**：
  - 主数据集：`available_fields`
  - 第二个数据集：`fields_b`
  - 合并并排序：`all_join_fields`（用于显示）

- **选择连接键**：
  - Left Key：主数据集的字段
  - Right Key：第二个数据集的字段

- **选择连接类型**：
  - inner、left、right、full

---

### 9.3 执行 Join

```python
results = collection.hash_join(
    st.session_state.collection_b,
    key_self,
    key_other,
    join_type
)

# Save results to session state for use in other tabs
st.session_state.join_results = results
st.session_state.use_join_results = True
```

**关键点**：

- **保存结果到 Session State**：
  - 允许在其他标签页使用 Join 结果
  - 设置标志 `use_join_results = True`

---

### 9.4 扁平化导出

```python
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
```

**详细解析**：

- Join 结果是嵌套结构：`{"left": {...}, "right": {...}}`
- CSV 需要扁平结构：每行一个记录，字段作为列
- 扁平化：将嵌套结构展开为 `left.*` 和 `right.*` 字段

---

### 9.5 清除 Join 结果

```python
if st.session_state.join_results is not None:
    st.markdown("---")
    if st.button("Clear Join Results", key="clear_join"):
        st.session_state.join_results = None
        st.session_state.use_join_results = False
        st.success("Join results cleared")
        st.rerun()
```

**详细解析**：

- **`st.markdown("---")`**：显示分隔线
- **清除按钮**：
  - 重置 Join 相关状态
  - **`st.rerun()`**：重新运行脚本，更新界面

---

## 10. Tab 5: Analysis（分析）操作（930-1081 行）

### 10.1 分析模式选择

```python
analysis_type = st.selectbox(
    "Mode",
    ["Overview", "Field Statistics", "Engagement by Location"],
    key=f"analysis_type_{file_key_suffix}"
)
```

**三种模式**：
1. **Overview**：数据集概览
2. **Field Statistics**：字段统计
3. **Engagement by Location**：按位置计算参与度

---

### 10.2 Overview 模式

```python
if analysis_type == "Overview":
    sample_doc = collection.data[0] if collection.data else {}
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Records", len(collection.data))
    col2.metric("Fields", len(sample_doc))
    col3.metric("Type", "JSON")
    
    st.subheader("Schema")
    st.json(sample_doc)
```

**详细解析**：

- **`st.metric()`**：显示指标卡片
  - 大数字 + 标签
  - 适合展示关键统计信息

- **显示示例文档**：
  - 以 JSON 格式展示第一个文档
  - 用户可以查看数据结构

---

### 10.3 Field Statistics 模式

```python
elif analysis_type == "Field Statistics":
    field_to_analyze = st.selectbox("Field", ...)
    
    if st.button("Analyze", type="primary"):
        counts = collection.aggregate(field_to_analyze, agg_count())
        
        df = pd.DataFrame([
            {"Value": k, "Count": v}
            for k, v in counts.items()
        ]).sort_values("Count", ascending=False)
        
        st.dataframe(df.head(20), use_container_width=True)
        st.bar_chart(df.head(10).set_index("Value"))
```

**详细解析**：

- 选择要分析的字段
- 使用 `agg_count()` 统计每个值的出现次数
- 显示表格和条形图

---

### 10.4 Engagement by Location 模式

这是最复杂的部分，展示分块处理的实际应用。

#### 10.4.1 配置分块大小

```python
chunk_size = st.number_input(
    "Chunk Size",
    min_value=100,
    max_value=50000,
    value=5000,
    step=100,
    help="Number of records per chunk"
)
```

- **`st.number_input()`**：数字输入框
- 限制范围：100-50000
- 默认值：5000

#### 10.4.2 文件选择

```python
if st.session_state.data_loaded and st.session_state.collection:
    use_current = st.checkbox("Use currently loaded data", value=True)
    if use_current:
        # Save current data to temp file for processing
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.jsonl',
            delete=False,
            encoding='utf-8'
        )
        for doc in st.session_state.collection.data:
            temp_file.write(json.dumps(doc, ensure_ascii=False) + '\n')
        temp_file.close()
        file_to_process = temp_file.name
        temp_file_created = True
    else:
        uploaded_analysis_file = st.file_uploader(...)
```

**详细解析**：

**选项 1：使用当前加载的数据**
- 创建临时 JSONL 文件
- 将内存中的数据写入文件（因为 `calculate_average_engagement_by_location()` 需要文件路径）
- **`tempfile.NamedTemporaryFile()`**：创建临时文件
  - **`delete=False`**：不自动删除（需要手动清理）

**选项 2：上传新文件**
- 与之前相同的上传逻辑

#### 10.4.3 执行计算

```python
if file_to_process and st.button("Calculate", type="primary"):
    try:
        with st.spinner("Processing chunks..."):
            results = calculate_average_engagement_by_location(
                file_to_process,
                chunk_size
            )
        
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
            
            st.success(f"Processed {sum(...)} total posts across {len(results)} locations")
            st.dataframe(df, use_container_width=True)
            
            # Visualization
            chart_type = st.selectbox("Chart Type", ["Bar Chart", "Table"])
            if chart_type == "Bar Chart":
                top_n = st.slider("Top N Locations", 5, min(20, len(df)), 10)
                chart_df = df.head(top_n)
                st.bar_chart(chart_df.set_index("Location")["Avg Engagement Rate"])
            
            # Download results
            st.download_button(
                label="Download Results (CSV)",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name="engagement_by_location.csv",
                mime="text/csv"
            )
        
        # Cleanup temp file
        if temp_file_created and os.path.exists(file_to_process):
            os.unlink(file_to_process)
```

**详细流程**：

1. **显示加载动画**：`st.spinner()`

2. **调用分块处理函数**：
   - 处理大文件
   - 返回按位置分组的平均参与度

3. **转换结果**：
   - 将字典转换为 DataFrame
   - 四舍五入到 2 位小数
   - 按参与度降序排序

4. **显示统计信息**：
   - 总帖子数
   - 位置数量

5. **可视化**：
   - 可选择的图表类型
   - 可调整显示的 Top N 位置

6. **下载结果**：CSV 格式

7. **清理临时文件**：删除创建的临时文件

---

## 11. 侧边栏页脚（1083-1092 行）

```python
st.sidebar.markdown("---")
st.sidebar.markdown("### Operations")
st.sidebar.markdown("""
- **Find**: Filter by field-value equality
- **Project**: Select fields to display
- **Aggregate**: Group and apply functions
- **Join**: Hash join two datasets
- **Analysis**: Schema and statistics
""")
```

**详细解析**：

- **`st.markdown("---")`**：显示分隔线
- **`st.markdown("### Operations")`**：显示标题
- **操作说明**：列出所有功能标签页的简要说明

---

## 总结

### 关键设计模式

1. **Session State 管理**：
   - 在页面刷新之间保持状态
   - 存储数据集、Join 结果等

2. **条件渲染**：
   - 根据数据加载状态显示不同内容
   - 根据用户选择显示不同选项

3. **文件键后缀**：
   - 切换文件时重置组件状态

4. **扁平化 Join 结果**：
   - 使 Join 结果可以用于其他操作

5. **临时文件管理**：
   - 处理上传的文件和内存数据
   - 使用后及时清理

### 用户体验优化

1. **字段下拉列表**：不需要记住字段名
2. **实时预览**：可调整预览数量
3. **可视化**：图表展示聚合结果
4. **下载功能**：支持 JSON 和 CSV 导出
5. **错误处理**：友好的错误提示
6. **加载反馈**：加载动画和进度提示

### 技术栈

- **Streamlit**：Web 框架
- **Pandas**：数据处理和 DataFrame
- **Plotly**：交互式图表
- **自定义组件**：JSON 解析器、Collection 类

这个应用完整地展示了如何将后端的数据处理逻辑包装成一个友好的 Web 界面。

