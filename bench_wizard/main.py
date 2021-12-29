import os
import sys
from typing import Optional

import click

from bench_wizard import __version__
from bench_wizard.benchmark import run_pallet_benchmarks, BenchmarksConfig
from bench_wizard.db_bench import DBPerformanceConfig, run_db_benchmark
from bench_wizard.exceptions import BenchmarkCargoException
from bench_wizard.output import Output, PerformanceOutput
from bench_wizard.performance import run_pallet_performance, PerformanceConfig


@click.group()
def main():
    pass


@main.command()
def version():
    click.echo(__version__)


@main.command("benchmark")
@click.option(
    "-p",
    "--pallet",
    type=str,
    multiple=True,
    required=True,
    help="Pallets",
)
@click.option(
    "-d",
    "--dump-results",
    type=str,
    required=False,
    help="Directory to dump benchmarks results",
)
@click.option(
    "-o",
    "--output-dir",
    type=str,
    required=False,
    help="Save weights into rust file",
)
@click.option(
    "-t",
    "--template",
    type=str,
    required=False,
    help="Weight hbs template file ",
)
def benchmark(
    pallet: list,
    dump_results: Optional[str],
    template: Optional[str],
    output_dir: Optional[str],
):

    config = BenchmarksConfig(
        pallets=pallet,
        dump_results=dump_results,
        template=template,
        output_dir=output_dir,
    )

    run_pallet_benchmarks(config, Output())


@main.command("pc")
@click.option(
    "-rf",
    "--reference-values",
    type=str,
    required=True,
    help="Reference values - json format",
)
@click.option(
    "-p",
    "--pallet",
    type=str,
    multiple=True,
    required=True,
    help="Pallets",
)
def pc(
    reference_values: str,
    pallet: list,
):

    if not os.path.isfile(reference_values):
        print(f"{reference_values} does not exist", file=sys.stderr)
        exit(1)


    config = PerformanceConfig(
        reference_values=reference_values,
        pallets=pallet,
    )

    try:
        run_pallet_performance(config, PerformanceOutput())
    except BenchmarkCargoException as e:
        print(str(e), file=sys.stderr)
        exit(1)


@main.command("db")
@click.option(
    "-d",
    "--substrate-dir",
    type=str,
    required=True,
    help="Substrate directory",
)
def db_benchmark(
    substrate_dir: str,
):
    config = DBPerformanceConfig(
        substrate_dir=substrate_dir,
    )

    run_db_benchmark(config)
