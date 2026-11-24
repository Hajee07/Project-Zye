"""
Microsoft Excel Windows COM Constants & Enumerations — Zye Day 22.
Enables robust COM interaction without relying on late-bound win32com constants.
"""

from __future__ import annotations


class ExcelConstants:
    """Official Microsoft Excel Object Model Enumerations."""

    # Calculation Modes
    xlCalculationManual = -4135
    xlCalculationAutomatic = -4105
    xlCalculationSemiautomatic = 2

    # Chart Types (XlChartType)
    xlColumnClustered = 51
    xlColumnStacked = 52
    xlColumnStacked100 = 53
    xl3DColumn = -4100
    xl3DColumnClustered = 54
    xl3DColumnStacked = 55
    xl3DColumnStacked100 = 56
    xlBarClustered = 57
    xlBarStacked = 58
    xlBarStacked100 = 59
    xl3DBarClustered = 60
    xl3DBarStacked = 61
    xl3DBarStacked100 = 62
    xlLine = 4
    xlLineStacked = 63
    xlLineStacked100 = 64
    xlLineMarkers = 65
    xl3DLine = -4101
    xlPie = 5
    xlPieExploded = 69
    xl3DPie = -4102
    xl3DPieExploded = 70
    xlDoughnut = -4120
    xlDoughnutExploded = 80
    xlArea = 1
    xlAreaStacked = 76
    xlAreaStacked100 = 77
    xl3DArea = -4103
    xlXYScatter = -4169
    xlXYScatterLines = 74
    xlXYScatterSmooth = 72
    xlCombo = -4152

    # Chart Legend Positions
    xlLegendPositionBottom = -4107
    xlLegendPositionCorner = 2
    xlLegendPositionLeft = -4131
    xlLegendPositionRight = -4152
    xlLegendPositionTop = -4160

    # Pivot Table Aggregations (XlConsolidationFunction)
    xlSum = -4157
    xlCount = -4112
    xlAverage = -4106
    xlMax = -4136
    xlMin = -4139
    xlProduct = -4149
    xlStDev = -4155
    xlStDevP = -4156
    xlVar = -4164
    xlVarP = -4165

    # Pivot Table Field Orientations (XlPivotFieldOrientation)
    xlHidden = 0
    xlRowField = 1
    xlColumnField = 2
    xlPageField = 3
    xlDataField = 4

    # Conditional Formatting Types (XlFormatConditionType)
    xlCellValue = 1
    xlExpression = 2
    xlColorScale = 3
    xlDatabar = 4
    xlTop10 = 5
    xlIconSet = 6
    xlUniqueValues = 8

    # Conditional Formatting Operators (XlFormatConditionOperator)
    xlBetween = 1
    xlNotBetween = 2
    xlEqual = 3
    xlNotEqual = 4
    xlGreater = 5
    xlLess = 6
    xlGreaterEqual = 7
    xlLessEqual = 8

    # Data Validation Types (XlDVType)
    xlValidateInputOnly = 0
    xlValidateWholeNumber = 1
    xlValidateDecimal = 2
    xlValidateList = 3
    xlValidateDate = 4
    xlValidateTime = 5
    xlValidateTextLength = 6
    xlValidateCustom = 7

    # Data Validation Alert Styles (XlDVAlertStyle)
    xlValidAlertStop = 1
    xlValidAlertWarning = 2
    xlValidAlertInformation = 3

    # Sorting Order (XlSortOrder)
    xlAscending = 1
    xlDescending = 2

    # Yes/No (XlYesNoGuess)
    xlNo = 2
    xlYes = 1
    xlGuess = 0

    # Alignments
    xlHAlignLeft = -4131
    xlHAlignCenter = -4108
    xlHAlignRight = -4152
    xlHAlignJustify = -4130
    xlVAlignTop = -4160
    xlVAlignCenter = -4108
    xlVAlignBottom = -4107

    # Borders (XlBordersIndex)
    xlEdgeLeft = 7
    xlEdgeTop = 8
    xlEdgeBottom = 9
    xlEdgeRight = 10
    xlInsideVertical = 11
    xlInsideHorizontal = 12

    # Line Styles
    xlContinuous = 1
    xlDash = -4115
    xlDot = -4118
    xlDouble = -4119

    # Border Weight
    xlHairline = 1
    xlThin = 2
    xlMedium = -4138
    xlThick = 4

    # Orientation (Page Setup)
    xlPortrait = 1
    xlLandscape = 2

    # Paper Size
    xlPaperLetter = 1
    xlPaperLegal = 5
    xlPaperA3 = 8
    xlPaperA4 = 9

    # Export Format
    xlTypePDF = 0
    xlTypeXPS = 1

    # Direction (XlDirection)
    xlDown = -4121
    xlToLeft = -4159
    xlToRight = -4161
    xlUp = -4162
