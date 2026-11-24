"""
Business Data Analytics Engine for Zye Personal Assistant (Day 14 & Day 30).
Provides deterministic statistical profiling, KPI calculations, revenue/expense trends,
IQR anomaly detection, and Gemini-assisted executive business insights using Pandas.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("zye.personal_assistant.analytics")

REVENUE_KEYWORDS = {"revenue", "sales", "turnover", "gross_sales", "income", "amount", "total_price"}
EXPENSE_KEYWORDS = {"expense", "cost", "spending", "expenses", "cogs", "expenditure", "costs"}
PROFIT_KEYWORDS = {"profit", "net_profit", "gross_profit", "margin", "earnings"}
DATE_KEYWORDS = {"date", "timestamp", "created_at", "order_date", "transaction_date", "day", "month"}
CATEGORY_KEYWORDS = {"category", "product", "region", "department", "segment", "type", "channel"}

MAX_ALLOWED_FILE_BYTES = 100 * 1024 * 1024  # 100 MB limit


class BusinessAnalyticsEngine:
    def __init__(self) -> None:
        pass

    def analyze_dataset(
        self,
        file_path: str,
        business_question: str = "",
        sheet_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Perform deterministic statistical, KPI, trend, and anomaly analysis on CSV or Excel files.
        Strictly read-only; never alters or modifies the source dataset.
        """
        p = Path(file_path).resolve()
        if not p.exists() or not p.is_file():
            return {
                "status": "ERROR",
                "error_code": "DATA_FILE_NOT_FOUND",
                "message": f"File does not exist: {file_path}",
            }

        ext = p.suffix.lower()
        if ext not in (".csv", ".xlsx", ".xls"):
            return {
                "status": "ERROR",
                "error_code": "DATA_UNSUPPORTED_FORMAT",
                "message": f"Unsupported file type '{ext}'. Supported formats: .csv, .xlsx, .xls",
            }

        # Check file size limit
        try:
            file_bytes = p.stat().st_size
            if file_bytes > MAX_ALLOWED_FILE_BYTES:
                return {
                    "status": "ERROR",
                    "error_code": "DATA_SIZE_EXCEEDED",
                    "message": f"File size ({file_bytes / (1024*1024):.1f} MB) exceeds maximum allowed limit (100 MB).",
                }
            if file_bytes == 0:
                return {
                    "status": "ERROR",
                    "error_code": "DATA_FILE_CORRUPTED",
                    "message": "File is empty (0 bytes).",
                }
        except Exception as e:
            return {
                "status": "ERROR",
                "error_code": "DATA_ACCESS_DENIED",
                "message": f"Failed to access file properties: {e}",
            }

        # 1. Load Data Safely
        available_sheets: list[str] = []
        selected_sheet = sheet_name or "Sheet1"
        try:
            if ext == ".csv":
                df = pd.read_csv(str(p), encoding="utf-8", on_bad_lines="skip")
            else:
                with pd.ExcelFile(str(p)) as xl:
                    available_sheets = xl.sheet_names
                    if sheet_name and sheet_name in available_sheets:
                        selected_sheet = sheet_name
                    elif available_sheets:
                        selected_sheet = available_sheets[0]
                df = pd.read_excel(str(p), sheet_name=selected_sheet)
        except Exception as e:
            logger.error("Failed to read dataset %s: %s", p, e)
            return {
                "status": "ERROR",
                "error_code": "DATA_FILE_CORRUPTED",
                "message": f"Data loading failed: {e}",
            }

        if df.empty:
            return {
                "status": "ERROR",
                "error_code": "DATA_FILE_CORRUPTED",
                "message": "Dataset is empty (0 rows).",
            }

        # 2. Dataset Profiling & Metadata
        row_count, col_count = df.shape
        missing_counts = {col: int(cnt) for col, cnt in df.isnull().sum().items() if cnt > 0}
        duplicate_rows = int(df.duplicated().sum())

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = [str(c) for c in df.select_dtypes(include=["object", "string", "category"]).columns]
        date_cols: list[str] = []

        # Detect date columns
        for c in df.columns:
            c_low = str(c).lower()
            if any(kw in c_low for kw in DATE_KEYWORDS):
                date_cols.append(str(c))
            elif str(c) in categorical_cols:
                # Test parse sample
                sample = df[c].dropna().head(5)
                if not sample.empty:
                    try:
                        import warnings
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            pd.to_datetime(sample, errors="raise")
                        date_cols.append(str(c))
                    except Exception:
                        pass

        data_quality = {
            "total_rows": int(row_count),
            "total_columns": int(col_count),
            "columns": [str(c) for c in df.columns],
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "date_columns": date_cols,
            "missing_values_by_column": missing_counts,
            "duplicate_records": duplicate_rows,
            "has_duplicates": duplicate_rows > 0,
        }

        # 3. Numeric Summaries & Deterministic KPIs
        computed_metrics: dict[str, Any] = {}
        for col in numeric_cols:
            col_series = df[col].dropna()
            if not col_series.empty:
                computed_metrics[col] = {
                    "count": int(col_series.count()),
                    "sum": round(float(col_series.sum()), 2),
                    "mean": round(float(col_series.mean()), 2),
                    "median": round(float(col_series.median()), 2),
                    "std": round(float(col_series.std()), 2) if col_series.count() > 1 else 0.0,
                    "min": round(float(col_series.min()), 2),
                    "max": round(float(col_series.max()), 2),
                }

        kpis: dict[str, Any] = {}
        for col in numeric_cols:
            c_lower = str(col).lower()
            if any(kw in c_lower for kw in REVENUE_KEYWORDS) and "total_revenue" not in kpis:
                kpis["total_revenue"] = computed_metrics[col]["sum"]
                kpis["revenue_column"] = col
                kpis["average_revenue_per_row"] = computed_metrics[col]["mean"]
            elif any(kw in c_lower for kw in EXPENSE_KEYWORDS) and "total_expenses" not in kpis:
                kpis["total_expenses"] = computed_metrics[col]["sum"]
                kpis["expense_column"] = col
            elif any(kw in c_lower for kw in PROFIT_KEYWORDS) and "total_profit" not in kpis:
                kpis["total_profit"] = computed_metrics[col]["sum"]
                kpis["profit_column"] = col

        # Derive net profit and margin if revenue and expenses exist
        if "total_revenue" in kpis and "total_expenses" in kpis:
            net_prof = round(kpis["total_revenue"] - kpis["total_expenses"], 2)
            kpis["calculated_net_profit"] = net_prof
            if kpis["total_revenue"] > 0:
                kpis["profit_margin_pct"] = round((net_prof / kpis["total_revenue"]) * 100.0, 1)
            else:
                kpis["profit_margin_pct"] = 0.0
        elif "total_profit" in kpis and "total_revenue" in kpis and kpis["total_revenue"] > 0:
            kpis["profit_margin_pct"] = round((kpis["total_profit"] / kpis["total_revenue"]) * 100.0, 1)

        # 4. Revenue & Expense Trend Analysis
        trends: list[dict[str, Any]] = []
        if date_cols and ("revenue_column" in kpis or numeric_cols):
            val_col = kpis.get("revenue_column") or numeric_cols[0]
            target_date_col = date_cols[0]
            try:
                temp_df = df[[target_date_col, val_col]].dropna().copy()
                temp_df["parsed_date"] = pd.to_datetime(temp_df[target_date_col], errors="coerce")
                temp_df = temp_df.dropna(subset=["parsed_date"])
                if not temp_df.empty:
                    temp_df["period"] = temp_df["parsed_date"].dt.to_period("M").astype(str)
                    period_grp = temp_df.groupby("period")[val_col].agg(["sum", "count"]).reset_index()
                    for _, row_data in period_grp.iterrows():
                        trends.append({
                            "period": str(row_data["period"]),
                            "metric_column": val_col,
                            "total": round(float(row_data["sum"]), 2),
                            "transaction_count": int(row_data["count"]),
                        })
            except Exception as trend_err:
                logger.debug("Trend grouping bypassed: %s", trend_err)

        # 5. Category / Segment Breakdown
        segments: list[dict[str, Any]] = []
        cat_targets = [c for c in categorical_cols if any(kw in str(c).lower() for kw in CATEGORY_KEYWORDS)]
        if cat_targets and ("revenue_column" in kpis or numeric_cols):
            cat_col = cat_targets[0]
            val_col = kpis.get("revenue_column") or numeric_cols[0]
            try:
                grp = df.groupby(cat_col)[val_col].agg(["sum", "count"]).reset_index()
                total_val = grp["sum"].sum()
                for _, r in grp.sort_values(by="sum", ascending=False).head(8).iterrows():
                    pct = round((r["sum"] / total_val) * 100.0, 1) if total_val > 0 else 0.0
                    segments.append({
                        "segment": str(r[cat_col]),
                        "total": round(float(r["sum"]), 2),
                        "count": int(r["count"]),
                        "contribution_pct": pct,
                    })
            except Exception as seg_err:
                logger.debug("Segment breakdown bypassed: %s", seg_err)

        # 6. Statistical Anomaly Detection
        detected_anomalies: list[dict[str, Any]] = []

        if duplicate_rows > 0:
            detected_anomalies.append({
                "type": "DUPLICATE_ROWS",
                "severity": "MEDIUM",
                "details": f"{duplicate_rows} duplicate record(s) detected in dataset.",
            })

        if "revenue_column" in kpis:
            rev_col = kpis["revenue_column"]
            neg_rev_count = int((df[rev_col] < 0).sum())
            if neg_rev_count > 0:
                detected_anomalies.append({
                    "type": "NEGATIVE_REVENUE",
                    "severity": "HIGH",
                    "column": rev_col,
                    "count": neg_rev_count,
                    "details": f"{neg_rev_count} row(s) contain unexpected negative values in '{rev_col}'.",
                })

        # IQR Outliers (only if sample size >= 4)
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) >= 4:
                q25 = float(series.quantile(0.25))
                q75 = float(series.quantile(0.75))
                iqr = q75 - q25
                if iqr > 0:
                    lower_bound = q25 - (1.5 * iqr)
                    upper_bound = q75 + (1.5 * iqr)
                    outliers = series[(series < lower_bound) | (series > upper_bound)]
                    if len(outliers) > 0:
                        detected_anomalies.append({
                            "type": "STATISTICAL_OUTLIER",
                            "severity": "LOW",
                            "column": col,
                            "outlier_count": int(len(outliers)),
                            "bounds": [round(lower_bound, 2), round(upper_bound, 2)],
                        })

        # 7. Gemini Executive Insights (grounded in computed metrics only)
        executive_analysis = self._generate_executive_insights(
            filename=p.name,
            kpis=kpis,
            data_quality=data_quality,
            anomalies=detected_anomalies,
            trends=trends,
            business_question=business_question,
        )

        return {
            "status": "SUCCESS",
            "file_name": p.name,
            "selected_sheet": selected_sheet,
            "available_sheets": available_sheets,
            "data_quality": data_quality,
            "computed_metrics": computed_metrics,
            "business_kpis": kpis,
            "trends": trends,
            "segment_breakdown": segments,
            "detected_anomalies": detected_anomalies,
            "executive_analysis": executive_analysis,
        }

    def _generate_executive_insights(
        self,
        filename: str,
        kpis: dict[str, Any],
        data_quality: dict[str, Any],
        anomalies: list[dict[str, Any]],
        trends: list[dict[str, Any]],
        business_question: str,
    ) -> str:
        """Query Central Gemini Gateway with verified computed statistics."""
        try:
            from gemini_gateway import ZyeGeminiGateway
            gw = ZyeGeminiGateway.get_instance()
            prompt = (
                f"Analyze this verified dataset profile for '{filename}'.\n"
                f"KPIs: {json.dumps(kpis)}\n"
                f"Data Quality: {json.dumps(data_quality)}\n"
                f"Anomalies: {json.dumps(anomalies)}\n"
                f"Trends: {json.dumps(trends[:5])}\n"
                f"User Question: {business_question or 'Provide an executive financial and operational briefing.'}\n"
                "IMPORTANT: Do not invent any numbers. Rely strictly on the computed metrics above. "
                "Highlight key trends, risk areas, anomalies, and 2-3 strategic recommendations."
            )
            res = gw.generate_response(prompt=prompt, workload="PERSONAL_ASSISTANT", thinking_level="LOW")
            if res.get("status") in ("SUCCESS", "CACHED") and res.get("text"):
                return res["text"].strip()
        except Exception as e:
            logger.debug("Gemini analytics executive analysis fell back: %s", e)

        # Offline deterministic summary
        rev_str = f"Total Revenue: {kpis.get('total_revenue', 'N/A')}"
        exp_str = f"Total Expenses: {kpis.get('total_expenses', 'N/A')}"
        prof_str = f"Net Profit: {kpis.get('calculated_net_profit', kpis.get('total_profit', 'N/A'))}"
        margin_str = f"Margin: {kpis.get('profit_margin_pct', 'N/A')}%"
        anom_str = f"{len(anomalies)} anomaly group(s) flagged." if anomalies else "No critical anomalies detected."
        trend_str = f"{len(trends)} monthly period(s) analyzed." if trends else "No time-series date column found."
        return (
            f"Dataset '{filename}' analysis complete ({data_quality['total_rows']} rows, {data_quality['total_columns']} columns). "
            f"{rev_str}, {exp_str}, {prof_str} ({margin_str}). {trend_str} {anom_str} "
            "Data processed offline using verified Pandas statistical engines."
        )
