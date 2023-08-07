import click
import pandas as pd
from tools import write_connections_bedpe_format
from predictor import make_gene_prediction_stats


@click.command()
@click.option("--output_tsv_file", type=str)
@click.option("--output_bed_file", type=str)
@click.option("--output_gene_stats_file", type=str)
@click.option("--pred_file", type=str)
@click.option("--pred_nonexpressed_file", type=str)
@click.option(
    "--score_column",
    type=str,
    help="Column name of score to use for thresholding",
)
@click.option("--threshold", type=float)
@click.option("--include_self_promoter", type=bool)
@click.option("--only_expressed_genes", type=bool)
def main(
    output_tsv_file,
    output_bed_file,
    output_gene_stats_file,
    pred_file,
    pred_nonexpressed_file,
    score_column,
    threshold,
    include_self_promoter,
    only_expressed_genes,
):
    all_putative = pd.read_csv(pred_file, sep="\t")
    if not only_expressed_genes:
        non_expressed = pd.read_csv(pred_nonexpressed_file, sep="\t")
        all_putative = pd.concat([all_putative, non_expressed], ignore_index=True)

    filtered_predictions = all_putative[all_putative[score_column] > threshold]

    if not include_self_promoter:
        filtered_predictions = filtered_predictions[
            ~filtered_predictions["isSelfPromoter"]
        ]

    filtered_predictions.to_csv(
        output_tsv_file, sep="\t", index=False, header=True, float_format="%.6f"
    )
    write_connections_bedpe_format(filtered_predictions, output_bed_file, score_column)
    make_gene_prediction_stats(
        filtered_predictions, score_column, threshold, output_gene_stats_file
    )


if __name__ == "__main__":
    main()
