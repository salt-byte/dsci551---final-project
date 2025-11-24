# JSON Query System - Streamlit Frontend

Interactive data query and analysis system based on `final_code.ipynb`.

## Features

### 1. Find
- Filter documents by field-value equality
- Supports dot notation for nested fields (e.g., `user.nick_name`)
- Field selection dropdown (no need to remember field names)
- Sample value suggestions for selected fields

### 2. Project
- Select fields to display
- Multi-field selection with dropdown
- Supports custom field input
- Export results as CSV

### 3. Aggregate
- Group by field and apply aggregation functions
- Supported functions: count, sum, avg, max, min
- Field selection with dropdown
- Visualization (bar chart, pie chart)
- Results sorted by aggregation value

### 4. Join
- Hash join operation on two datasets
- Supports inner, left, right, full join types
- Custom join keys with field selection
- **Join results can be used in other tabs** (Find, Project, Aggregate)
- Export results as JSON or CSV
- Clear join results option

### 5. Analysis
Three analysis modes:

#### Overview
- Dataset statistics (total records, field count)
- Sample document schema
- Available fields explorer

#### Field Statistics
- Count distinct values for any field
- Bar chart visualization
- Top N values display

#### Engagement by Location
- **Chunk processing** for large files
- Calculate Average Engagement Rate (AER) by IP location
- Formula: `AER = (Reposts + Comments + Attitudes) / Posts`
- Configurable chunk size
- Map-Reduce pattern with partial aggregation merging
- Results visualization and CSV export

## Installation & Running

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Application
```bash
streamlit run app.py
```

The application will automatically open in your browser at `http://localhost:8501`

## Usage Guide

### Basic Workflow
1. **Load Data**: Upload a JSON/JSONL file in the sidebar, or select an existing file
2. **Select Operation**: Use the top tabs to choose an operation
3. **Select Fields**: Use dropdown menus to select fields (no need to type field names)
4. **Execute**: Click the Execute button
5. **View Results**: Results displayed as tables, charts, or JSON
6. **Export**: Download results as JSON or CSV

### Advanced Workflow: Combining Operations

#### Using Join Results in Other Operations
1. Load first dataset in sidebar
2. Go to **Join** tab, upload second dataset
3. Execute join operation
4. Join results are automatically saved
5. Switch to **Find**, **Project**, or **Aggregate** tabs
6. These tabs will automatically use join results
7. Fields are accessible as `left.field_name` and `right.field_name`
8. Clear join results when done

#### Chunk Processing for Large Files
1. Go to **Analysis** tab
2. Select **Engagement by Location** mode
3. Choose chunk size (default: 5000)
4. Use currently loaded data or upload a file
5. Click **Calculate**
6. System processes file in chunks and merges results
7. View results and export as CSV

## Supported File Formats

- **JSON Array**: `[{...}, {...}]`
- **JSONL**: One JSON object per line

## Technical Details

### Chunk Processing
- **Purpose**: Handle large files without memory overflow
- **Method**: Map-Reduce pattern
  - **Map Phase**: Process each chunk independently
  - **Reduce Phase**: Merge partial aggregation results
- **Benefits**:
  - Memory efficient
  - Scalable to any file size
  - Can be parallelized (currently sequential)

### Partial Aggregation
- Uses `PartialAgg` class to merge results from chunks
- Supports: count, sum, max, min, avg merging
- Ensures accurate results across chunks

### Field Selection
- Automatic field extraction from data structure
- Dropdown menus for all field inputs
- Supports nested fields with dot notation
- Sample values shown for query fields

## Technology Stack

- **Streamlit**: Web UI framework
- **Custom JSON Parser**: Extracted from notebook (Tokenizer, Parser)
- **Pandas**: Data processing and DataFrame operations
- **Plotly**: Interactive data visualization

## Key Features

### User-Friendly Interface
- No need to remember field names - all fields available in dropdowns
- Sample values suggested for queries
- Clear visual feedback for operations
- Professional, non-AI-looking interface

### Data Operations
- **Find**: Equality matching with field selection
- **Project**: Multi-field selection with custom field support
- **Aggregate**: Group by any field with various aggregation functions
- **Join**: Hash join with result persistence across tabs
- **Analysis**: Schema exploration, statistics, and engagement analysis

### Export Capabilities
- JSON export for structured data
- CSV export for tabular data
- Join results export (JSON and CSV)
- Engagement analysis results export

## Notes

- Large files are automatically processed in chunks
- Nested fields use dot notation (e.g., `user.nick_name`)
- Find operation supports equality matching only
- Join operation requires two datasets
- Join results persist across tabs until cleared
- Chunk processing is used for engagement analysis on large files
- All operations support field selection via dropdown menus

## File Structure

```
.
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── README_STREAMLIT.md       # This file
└── [data files]             # JSON/JSONL data files
```

## Example Use Cases

1. **Data Exploration**: Load data → Overview → Field Statistics
2. **Data Filtering**: Load data → Find → Export filtered results
3. **Data Analysis**: Load data → Aggregate by location → Visualize
4. **Data Merging**: Load two datasets → Join → Use results in other operations
5. **Large File Analysis**: Upload large file → Engagement by Location → Export results
