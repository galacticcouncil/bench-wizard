import pytest

from bench_wizard.parser import BenchmarkParser

BENCHMARK_RESULT = r"""
Pallet: "amm", Extrinsic: "create_pool", Lowest values: [], Highest values: [], Steps: [5], Repeat: 20
Median Slopes Analysis
========
-- Extrinsic Time --

Model:
Time ~=    347.2
              µs

Reads = 11
Writes = 13
Min Squares Analysis
========
-- Extrinsic Time --

Model:
Time ~=    347.2
              µs

Reads = 11
Writes = 13
Pallet: "amm", Extrinsic: "add_liquidity", Lowest values: [], Highest values: [], Steps: [5], Repeat: 20
Median Slopes Analysis
========
-- Extrinsic Time --

Model:
Time ~=    325.8
              µs

Reads = 9
Writes = 8
Min Squares Analysis
========
-- Extrinsic Time --

Model:
Time ~=    325.8
              µs

Reads = 9
Writes = 8
"""


@pytest.mark.parametrize(
    "extrinsics, expected",
    [
        (["add_liquidity"], 325.8),
        (["create_pool"], 347.2),
        (["create_pool", "add_liquidity"], 673.0),
        ([], 0.0),
        (["not existing"], 0.0),
        (["create_pool", "add_liquidity", "", "not existing"], 673.0),
    ],
)
def test_parser(extrinsics, expected):
    parser = BenchmarkParser(BENCHMARK_RESULT.encode())
    assert parser.pallet == "amm"
    assert parser.total_time(extrinsics) == expected
