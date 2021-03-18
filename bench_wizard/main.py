import sys
from functools import partial
from typing import Optional

import click

from bench_wizard import __version__
from bench_wizard.benchmark import run_pallet_benchmarks
from bench_wizard.config import Config, PALLETS
from bench_wizard.db_bench import run_db_benchmark
from bench_wizard.exceptions import BenchmarkCargoException
from bench_wizard.output import Output


@click.group()
def main():
    pass


@main.command()
def version():
    click.echo(__version__)


@main.command("benchmark")
@click.option(
    "--include-db-benchmark",
    type=bool,
    default=False,
    is_flag=True,
    help="Perform Substrate Database benchmark",
)
@click.option(
    "--no-pallet-benchmarks",
    type=bool,
    default=False,
    is_flag=True,
    help="Skip pallets benchmarks",
)
@click.option(
    "--substrate-repo-path",
    type=str,
    default="./substrate",
    help="Substrate repository path (cloned if not provided or does not exist)",
)
@click.option(
    "--reference-values",
    type=str,
    default=".maintain/bench-check/hydradx-bench-data.json",
    help="Reference values - json format",
)
@click.option(
    "-p",
    "--pallet",
    type=str,
    multiple=True,
    required=False,
    default=PALLETS,
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
@click.option(
    "-pc",
    "--performance-check",
    type=bool,
    default=False,
    is_flag=True,
    help="Weight hbs template file",
)
def benchmark(
    include_db_benchmark: bool,
    no_pallet_benchmarks: bool,
    substrate_repo_path: str,
    reference_values: str,
    performance_check: bool,
    pallet: Optional[list],
    dump_results: Optional[str],
    template: Optional[str],
    output_dir: Optional[str],
):

    config = Config(
        do_db_bench=include_db_benchmark,
        substrate_repo_path=substrate_repo_path,
        do_pallet_bench=not no_pallet_benchmarks,
        reference_values=reference_values,
        pallets=pallet,
        dump_results=dump_results,
        template=template,
        output_dir=output_dir,
        performance_check=performance_check,
    )

    try:
        run_pallet_benchmarks(config, Output(not performance_check))
    except BenchmarkCargoException as e:
        print(str(e), file=sys.stderr)
        exit(1)
    run_db_benchmark(config)
