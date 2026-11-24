"""
Microsoft PowerPoint Windows COM Constants & Enumerations — Zye Day 23.
"""

from __future__ import annotations


class PowerPointConstants:
    """Official Microsoft PowerPoint Object Model Enumerations."""

    # SaveAs Formats
    ppSaveAsDefault = 11
    ppSaveAsPDF = 32
    ppSaveAsPNG = 18
    ppSaveAsJPG = 17

    # Slide Layouts (PpSlideLayout)
    ppLayoutTitle = 1
    ppLayoutText = 2
    ppLayoutTwoColumnText = 3
    ppLayoutTable = 4
    ppLayoutTextAndChart = 5
    ppLayoutChartAndText = 6
    ppLayoutOrgchart = 7
    ppLayoutChart = 8
    ppLayoutTextAndClipart = 9
    ppLayoutClipartAndText = 10
    ppLayoutTitleOnly = 11
    ppLayoutBlank = 12
    ppLayoutComparison = 34

    # Transitions (PpEntryEffect)
    ppEffectNone = 0
    ppEffectCut = 257
    ppEffectFade = 1793
    ppEffectFadeSmoothly = 3849
    ppEffectPushDown = 3843
    ppEffectPushLeft = 3844
    ppEffectPushRight = 3845
    ppEffectPushUp = 3846
    ppEffectWipeDown = 2817
    ppEffectWipeLeft = 2818
    ppEffectWipeRight = 2819
    ppEffectWipeUp = 2820
    ppEffectSplitHorizontalIn = 513
    ppEffectSplitHorizontalOut = 514
    ppEffectSplitVerticalIn = 515
    ppEffectSplitVerticalOut = 516
    ppEffectCoverDown = 1281
    ppEffectCoverLeft = 1282
    ppEffectCoverRight = 1283
    ppEffectCoverUp = 1284
    ppEffectUncoverDown = 1537
    ppEffectUncoverLeft = 1538
    ppEffectUncoverRight = 1539
    ppEffectUncoverUp = 1540
    ppEffectRandom = 513

    # Animation Effects (MsoAnimEffect)
    msoAnimEffectAppear = 1
    msoAnimEffectFly = 2
    msoAnimEffectBlinds = 3
    msoAnimEffectBox = 4
    msoAnimEffectCircle = 5
    msoAnimEffectCrawl = 6
    msoAnimEffectDiamond = 7
    msoAnimEffectDissolve = 8
    msoAnimEffectFade = 10
    msoAnimEffectFlashOnce = 11
    msoAnimEffectPeek = 12
    msoAnimEffectRandomBars = 13
    msoAnimEffectSpiral = 14
    msoAnimEffectSplit = 15
    msoAnimEffectStretch = 16
    msoAnimEffectStrips = 17
    msoAnimEffectSwivel = 18
    msoAnimEffectWipe = 22
    msoAnimEffectZoom = 23
    msoAnimEffectFloat = 60
    msoAnimEffectSpin = 25
    msoAnimEffectGrowShrink = 26
    msoAnimEffectTeeter = 30
    msoAnimEffectPulse = 61

    # Animation Trigger / Start Modes (MsoAnimTriggerType)
    msoAnimTriggerOnPageClick = 1
    msoAnimTriggerWithPrevious = 2
    msoAnimTriggerAfterPrevious = 3

    # Shapes (MsoShapeType & MsoAutoShapeType)
    msoShapeRectangle = 1
    msoShapeRoundedRectangle = 5
    msoShapeOval = 9
    msoShapeLine = 9
    msoShapeRightArrow = 13
    msoTextBox = 17

    # Alignments
    ppAlignLeft = 1
    ppAlignCenter = 2
    ppAlignRight = 3
    ppAlignJustify = 4

    # Yes/No TriState
    msoTrue = -1
    msoFalse = 0
