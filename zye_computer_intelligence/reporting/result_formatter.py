"""
Result Formatter Engine.
Formats structured analytical results into readable Markdown and low-latency Gemini Live voice scripts.
"""

from __future__ import annotations

from typing import Any


class ResultFormatter:
    """Formats analytical outputs for human review and voice playback."""

    @staticmethod
    def format_markdown_report(report: dict[str, Any]) -> str:
        """Generates comprehensive markdown analysis summary."""
        ds = report.get("dataset", {})
        exec_info = report.get("execution", {})
        profile = report.get("profile", {})
        correlations = report.get("correlations", {})
        outliers = report.get("outliers", {})

        md: list[str] = [
            f"# ZYE AI — Large Dataset Intelligence Report",
            f"**Dataset:** `{ds.get('name')}` | **Format:** {ds.get('format')} | **Backend:** {report.get('backend')}",
            f"**Total Records:** {ds.get('rows', 0):,} | **Columns:** {len(ds.get('columns', []))} | **Size:** {ds.get('size_mb', 0)} MB",
            f"**Execution Duration:** {exec_info.get('duration_ms', 0)} ms\n",
            "---",
        ]

        # 1. Correlations
        if correlations and correlations.get("ranked_relationships"):
            md.append("## Key Statistical Correlations")
            md.append("| Metric A | Metric B | Coefficient (r) | Strength / Direction | Valid Pairs |")
            md.append("|---|---|:---:|---|:---:|")
            for pair in correlations["ranked_relationships"][:8]:
                r_val = pair["correlation"]
                r_str = f"{r_val:.4f}" if r_val is not None else "N/A"
                md.append(f"| `{pair['column_a']}` | `{pair['column_b']}` | **{r_str}** | {pair['interpretation']} | {pair['valid_pairs']:,} |")
            md.append(f"\n> ℹ️ *{correlations.get('noncausality_statement', '')}*\n")

        # 2. Missing Values & Quality
        missing = profile.get("missing_values", {})
        if missing and missing.get("columns_with_missing"):
            md.append("## Data Quality & Missing Values")
            md.append("| Column | Missing Records | Nulls | Empty Strings | Missing % |")
            md.append("|---|:---:|:---:|:---:|:---:|")
            for col in missing["columns_with_missing"]:
                m_info = missing["missing_by_column"].get(col, {})
                md.append(
                    f"| `{col}` | {m_info.get('total_missing', 0):,} | {m_info.get('null_count', 0):,} | "
                    f"{m_info.get('empty_string_count', 0):,} | {m_info.get('missing_percentage', 0.0)}% |"
                )
            md.append("")

        # 3. Outliers
        if outliers and outliers.get("columns_with_anomalies"):
            md.append("## Statistical Outliers (IQR Method)")
            md.append("| Column | Lower Bound | Upper Bound | Outlier Count | Outlier % | Negative Values |")
            md.append("|---|:---:|:---:|:---:|:---:|:---:|")
            for col in outliers["columns_with_anomalies"]:
                o_info = outliers["anomalies_by_column"].get(col, {})
                neg_str = "⚠️ Yes" if o_info.get("has_negative_values") else "None"
                md.append(
                    f"| `{col}` | {o_info.get('lower_bound')} | {o_info.get('upper_bound')} | "
                    f"{o_info.get('outlier_count', 0):,} | {o_info.get('outlier_pct', 0.0)}% | {neg_str} |"
                )
            md.append("")

        return "\n".join(md)

    @staticmethod
    def format_voice_summaries(report: dict[str, Any]) -> tuple[str, str]:
        """Generates Tanglish and English voice summaries for Gemini Live."""
        ds = report.get("dataset", {})
        rows = ds.get("rows", 0)
        corrs = report.get("correlations", {})
        ranked = corrs.get("ranked_relationships", [])

        if ranked:
            top_pair = ranked[0]
            col_a = top_pair["column_a"]
            col_b = top_pair["column_b"]
            r_val = top_pair["correlation"]
            interp = top_pair["interpretation"].replace("_", " ").lower()

            voice_tanglish = (
                f"Dataset analysis mudinjidhu. Mottham {rows:,} rows scan panniyachu. "
                f"Mukkiyamaana correlation: {col_a} matrum {col_b} naduvula {interp} association irukku (r={r_val}). "
                f"Idhu linear relationship mattum dhaan, causation kidayaadhu."
            )
            voice_en = (
                f"Dataset analysis complete. Scanned {rows:,} rows. "
                f"Key statistical correlation: {col_a} and {col_b} show a {interp} association with r={r_val}. "
                f"Note that this correlation does not prove causation."
            )
        else:
            voice_tanglish = (
                f"Dataset analysis mudinjidhu. Mottham {rows:,} rows scan panniyachu. "
                f"Statistical profile and distribution calculated panniten."
            )
            voice_en = (
                f"Dataset analysis complete. Scanned {rows:,} rows. "
                f"Statistical profile and distributions have been calculated."
            )

        return voice_tanglish, voice_en
