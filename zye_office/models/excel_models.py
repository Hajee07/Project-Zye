"""
Data Models & Pydantic Schemas for Microsoft Excel Automation — Zye Day 22.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ExcelCalculationMode(str, Enum):
    AUTOMATIC = "AUTOMATIC"
    MANUAL = "MANUAL"
    SEMIAUTOMATIC = "SEMIAUTOMATIC"


class ExcelChartType(str, Enum):
    CLUSTERED_COLUMN = "CLUSTERED_COLUMN"
    STACKED_COLUMN = "STACKED_COLUMN"
    PERCENT_STACKED_COLUMN = "PERCENT_STACKED_COLUMN"
    CLUSTERED_BAR = "CLUSTERED_BAR"
    STACKED_BAR = "STACKED_BAR"
    LINE = "LINE"
    PIE = "PIE"
    DOUGHNUT = "DOUGHNUT"
    AREA = "AREA"
    SCATTER = "SCATTER"
    COMBO = "COMBO"
    HISTOGRAM = "HISTOGRAM"
    WATERFALL = "WATERFALL"
    THREE_D_COLUMN = "THREE_D_COLUMN"
    THREE_D_BAR = "THREE_D_BAR"
    THREE_D_LINE = "THREE_D_LINE"
    THREE_D_PIE = "THREE_D_PIE"


class ExcelPivotAggregation(str, Enum):
    SUM = "SUM"
    COUNT = "COUNT"
    AVERAGE = "AVERAGE"
    MAX = "MAX"
    MIN = "MIN"
    PRODUCT = "PRODUCT"
    STDEV = "STDEV"
    VAR = "VAR"


class ExcelWorkbookMetadata(BaseModel):
    status: str = "SUCCESS"
    app_name: str = "excel"
    workbook_name: str = ""
    filename: Optional[str] = None
    path: Optional[str] = None
    file_extension: Optional[str] = None
    sheet_count: int = 0
    sheet_names: List[str] = Field(default_factory=list)
    active_sheet_name: Optional[str] = None
    is_saved: bool = True
    is_read_only: bool = False
    is_protected: bool = False
    file_size_bytes: Optional[int] = None
    calculation_mode: str = "Automatic"
    external_links: List[str] = Field(default_factory=list)
    table_count: int = 0
    pivot_count: int = 0
    chart_count: int = 0
    active_cell: Optional[str] = None
    selected_range: Optional[str] = None
    used_rows: int = 0
    used_columns: int = 0
    message: Optional[str] = None


class ExcelWorksheetMetadata(BaseModel):
    status: str = "SUCCESS"
    sheet_name: str = ""
    index: int = 1
    is_visible: bool = True
    is_protected: bool = False
    used_range_address: str = "A1"
    row_count: int = 0
    column_count: int = 0
    tab_color: Optional[int] = None
    freeze_panes_active: bool = False
    tables_count: int = 0
    charts_count: int = 0
    pivot_tables_count: int = 0


class ExcelCellMetadata(BaseModel):
    status: str = "SUCCESS"
    address: str = "A1"
    row: int = 1
    column: int = 1
    value: Any = None
    formula: Optional[str] = None
    has_formula: bool = False
    number_format: Optional[str] = None
    font_name: Optional[str] = None
    font_size: Optional[float] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    color: Optional[int] = None
    bg_color: Optional[int] = None
    comment: Optional[str] = None


class ExcelRangeData(BaseModel):
    status: str = "SUCCESS"
    range_address: str = "A1"
    row_count: int = 1
    column_count: int = 1
    values: List[List[Any]] = Field(default_factory=list)
    formulas: Optional[List[List[Any]]] = None
    has_formulas: bool = False


class ExcelFormatOptions(BaseModel):
    font_name: Optional[str] = None
    font_size: Optional[float] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[bool] = None
    color: Optional[int] = None
    bg_color: Optional[int] = None
    horizontal_alignment: Optional[str] = None  # left, center, right, justify
    vertical_alignment: Optional[str] = None    # top, center, bottom
    number_format: Optional[str] = None
    borders: Optional[str] = None               # thin, medium, thick, double, none
    wrap_text: Optional[bool] = None
    row_height: Optional[float] = None
    column_width: Optional[float] = None
    merge_and_center: Optional[bool] = None
    preset: Optional[str] = None


class ExcelConditionalFormattingRule(BaseModel):
    rule_type: str = "cell_value"  # cell_value, formula, duplicate, unique, color_scale, data_bar, top_bottom
    range_address: str = "A1"
    operator: Optional[str] = None  # greater_than, less_than, equal, between, not_equal
    formula1: Optional[str] = None
    formula2: Optional[str] = None
    font_color: Optional[int] = None
    bg_color: Optional[int] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    stop_if_true: bool = True


class ExcelChartConfig(BaseModel):
    chart_type: str = "CLUSTERED_COLUMN"
    source_range: str = "A1:B10"
    title: Optional[str] = None
    x_title: Optional[str] = None
    y_title: Optional[str] = None
    legend_position: Optional[str] = "right"  # top, bottom, left, right, none
    data_labels: bool = False
    style_id: Optional[int] = None
    width_points: float = 380.0
    height_points: float = 240.0
    left_points: Optional[float] = None
    top_points: Optional[float] = None
    destination_sheet: Optional[str] = None


class ExcelPivotConfig(BaseModel):
    source_range: str = "A1:E50"
    table_name: str = "ZyePivotTable1"
    destination_sheet: Optional[str] = None
    destination_cell: str = "A3"
    row_fields: List[str] = Field(default_factory=list)
    column_fields: List[str] = Field(default_factory=list)
    value_fields: List[Dict[str, str]] = Field(default_factory=list)  # [{"field": "Sales", "aggregation": "SUM"}]
    filter_fields: List[str] = Field(default_factory=list)
    style_name: Optional[str] = "PivotStyleLight16"


class ExcelTableConfig(BaseModel):
    table_name: str = "ZyeTable1"
    range_address: str = "A1:D20"
    style_name: Optional[str] = "TableStyleMedium9"
    show_headers: bool = True
    show_totals: bool = False


class ExcelDataValidationConfig(BaseModel):
    validation_type: str = "list"  # list, whole, decimal, date, text_length, custom
    operator: Optional[str] = "between"
    formula1: str = ""
    formula2: Optional[str] = None
    allow_blank: bool = True
    show_input_message: bool = True
    input_title: Optional[str] = None
    input_message: Optional[str] = None
    show_error_message: bool = True
    error_title: Optional[str] = None
    error_message: Optional[str] = None
    error_style: str = "stop"  # stop, warning, information


class ExcelSortConfig(BaseModel):
    key_column: Union[str, int] = "A"
    order: str = "ascending"  # ascending, descending
    has_headers: bool = True
    match_case: bool = False
    secondary_key: Optional[Union[str, int]] = None
    secondary_order: Optional[str] = "ascending"


class ExcelFilterConfig(BaseModel):
    field_index: int = 1
    criteria1: str = ""
    operator: Optional[str] = None
    criteria2: Optional[str] = None


class ExcelDataCleanConfig(BaseModel):
    trim_spaces: bool = True
    remove_duplicates: bool = False
    columns_for_duplicates: Optional[List[Union[str, int]]] = None
    remove_blank_rows: bool = False
    remove_blank_columns: bool = False
    standardize_case: Optional[str] = None  # UPPER, LOWER, PROPER


class ExcelReportConfig(BaseModel):
    report_type: str = "MONTHLY_SALES"
    title: str = "Executive Monthly Report"
    period: Optional[str] = None
    source_range: Optional[str] = None
    destination_sheet: Optional[str] = None
    include_chart: bool = True
    chart_type: str = "CLUSTERED_COLUMN"
    include_pivot: bool = False
    preset: str = "BUSINESS_REPORT"


class ExcelPageSetupConfig(BaseModel):
    orientation: str = "PORTRAIT"  # PORTRAIT, LANDSCAPE
    paper_size: str = "A4"         # A4, LETTER, LEGAL, A3
    print_area: Optional[str] = None
    fit_to_page_wide: Optional[int] = 1
    fit_to_page_tall: Optional[int] = 0
    top_margin_points: float = 54.0
    bottom_margin_points: float = 54.0
    left_margin_points: float = 54.0
    right_margin_points: float = 54.0
    repeat_header_rows: Optional[str] = None  # "$1:$1"
