"""
Acceptance Test Suite: Real-Time Tactical FastMCP Tool Endpoints.
Tests 22-24 verifying FastMCP tool registration (15 tools), schema conformance,
scenario validation, Monte Carlo execution, comparison tools, and status tracking.
"""

import unittest

from realtime_tactical_mcp import (
    mcp,
    calculate_kinematic_risk,
    run_monte_carlo_risk_simulation,
    validate_kinematic_scenario,
    compare_trajectory_scenarios,
    get_tactical_simulation_status,
)


class TestTacticalMcpTools(unittest.TestCase):
    """Verifies that all 15 FastMCP tools in realtime_tactical_mcp.py are properly registered and functional."""

    def test_22_mcp_tool_registration_count(self):
        """Test 22: Exactly 15 tools are registered on the FastMCP server."""
        # FastMCP stores tools in _tool_manager._tools or _tools
        tool_mgr = getattr(mcp, "_tool_manager", mcp)
        tools = getattr(tool_mgr, "_tools", {})
        self.assertEqual(len(tools), 15, f"Expected 15 tools, got {len(tools)}: {list(tools.keys())}")

        expected_tools = [
            # Day 35 (5 tools)
            "analyze_realtime_stream",
            "get_telemetry_stream_status",
            "list_telemetry_streams",
            "reset_telemetry_stream",
            "get_telemetry_performance_metrics",
            # Day 36 (5 tools)
            "predict_opponent_attack",
            "get_opponent_sequence_status",
            "list_tracked_opponents",
            "reset_opponent_sequence",
            "get_opponent_pattern_summary",
            # Day 37 (5 tools)
            "calculate_kinematic_risk",
            "run_monte_carlo_risk_simulation",
            "validate_kinematic_scenario",
            "compare_trajectory_scenarios",
            "get_tactical_simulation_status",
        ]
        for t_name in expected_tools:
            self.assertIn(t_name, tools, f"Missing expected tool: {t_name}")

    def test_23_calculate_kinematic_risk_tool(self):
        """Test 23: Direct invocation of calculate_kinematic_risk tool."""
        res = calculate_kinematic_risk(
            entity_a={"entity_id": "uav1", "position": [0.0, 0.0], "velocity": [10.0, 0.0], "radius": 1.0},
            entity_b={"entity_id": "uav2", "position": [100.0, 0.0], "velocity": [-10.0, 0.0], "radius": 1.0},
            dimension=2,
            horizon_seconds=10.0,
        )

        self.assertTrue(res["collision_detected"])
        self.assertAlmostEqual(res["cpa_time_sec"], 5.0, places=3)
        self.assertAlmostEqual(res["min_separation_m"], 0.0, places=3)
        self.assertIn(str(res["risk_category"]), ["HIGH", "CRITICAL", "RiskCategory.HIGH", "RiskCategory.CRITICAL"])
        self.assertEqual(res["status"], "COLLISION_IMMINENT")

    def test_24_monte_carlo_and_scenario_tools(self):
        """Test 24: Direct invocation of Monte Carlo, validation, and scenario comparison tools."""
        # 1. Validation tool
        valid_scenario = {
            "entity_a": {"entity_id": "a", "position": [0.0, 0.0], "velocity": [5.0, 0.0], "radius": 1.0},
            "entity_b": {"entity_id": "b", "position": [50.0, 0.0], "velocity": [-5.0, 0.0], "radius": 1.0},
            "horizon_seconds": 10.0,
        }
        val_res = validate_kinematic_scenario(valid_scenario)
        self.assertEqual(val_res["status"], "VALID")
        self.assertTrue(val_res["is_valid"])

        # 2. Monte Carlo tool
        mc_res = run_monte_carlo_risk_simulation(
            entity_a={"entity_id": "a", "position": [0.0, 0.0], "velocity": [5.0, 0.0], "radius": 1.0},
            entity_b={"entity_id": "b", "position": [50.0, 0.0], "velocity": [-5.0, 0.0], "radius": 1.0},
            sample_count=2000,
            horizon_seconds=10.0,
            random_seed=42,
        )
        self.assertEqual(mc_res["sample_count"], 2000)
        self.assertTrue(mc_res["verified"])
        self.assertIn("median_separation_m", mc_res)
        self.assertIn("min_separation_m", mc_res)

        # 3. Scenario Comparison tool
        comp_scenario = {
            "scenario_id": "altered_course",
            "entity_a": {"entity_id": "a", "position": [0.0, 0.0], "velocity": [5.0, 0.0], "radius": 1.0},
            "entity_b": {"entity_id": "b", "position": [50.0, 20.0], "velocity": [-5.0, 0.0], "radius": 1.0},  # offset Y
            "horizon_seconds": 10.0,
        }
        comp_res = compare_trajectory_scenarios(
            baseline_scenario=valid_scenario,
            comparison_scenarios=[comp_scenario],
            sample_count=1000,
            horizon_seconds=10.0,
        )
        self.assertEqual(comp_res["baseline_scenario_id"], "baseline")
        self.assertGreaterEqual(len(comp_res["comparison_scenario_ids"]), 1)
        self.assertEqual(comp_res["safer_scenario_id"], "altered_course")

        # 4. Status tracker tool
        stat_res = get_tactical_simulation_status()
        self.assertEqual(stat_res["status"], "SUCCESS")
        self.assertIn("simulation_engine", stat_res)
        self.assertGreater(stat_res["simulation_engine"]["total_simulations"], 0)


if __name__ == "__main__":
    unittest.main()
