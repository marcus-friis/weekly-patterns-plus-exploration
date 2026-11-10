import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import pyfixest as pf
import seaborn as sns
from matplotlib.figure import Figure
from scipy.stats import spearmanr
from statsmodels.stats.multitest import multipletests

from wpp import cache, data, db, plotting
from wpp.utils import project_root

ROOT = project_root()
DATA_PATH = ROOT / "data"
FIGURE_PATH = ROOT / "figures2"
DB_PATH = ROOT / "wpp.duckdb"

sns.set_theme(style="ticks")
pl.Config.set_engine_affinity("streaming")

LABEL_CATEGORIES = {
    "Restaurants",
    "Grocery_Stores",
    "Public_Transportation",
    "Museums_Historical",
}

PALETTE = {
    "Other": "#D9D9D9",
    "Restaurants": "#D55E00",
    "Cafes_Coffee": "#E69F00",
    "Bars": "#8C2D62",
    "Grocery_Stores": "#009E73",
    "Specialty_Food": "#66C2A5",
    "Libraries": "#0072B2",
    "Museums_Historical": "#56B4E9",
    "Parks_Forests": "#228833",
    "Schools": "#AA4499",
    "Public_Transportation": "#C99400",
    "Retail": "#5F5F5F",
}


def compute_poi_temperature_correlations(
    pois_weekly: pl.DataFrame,
    *,
    min_observations: int = 10,
) -> pl.DataFrame:
    rows = []

    data = (
        pois_weekly.select(
            "CATEGORY",
            "ID_STORE",
            "AVG_TMAX",
            "SEGREGATION",
        )
        .drop_nulls()
        .filter(
            pl.col("AVG_TMAX").is_finite(),
            pl.col("SEGREGATION").is_finite(),
        )
        .sort("CATEGORY", "ID_STORE")
    )

    for (category, id_store), group in data.group_by(
        "CATEGORY",
        "ID_STORE",
        maintain_order=True,
    ):
        n = group.height

        if n < min_observations:
            continue

        temperature = group["AVG_TMAX"].to_numpy()
        segregation = group["SEGREGATION"].to_numpy()

        # Spearman correlation is undefined for constant series.
        if np.unique(temperature).size < 2 or np.unique(segregation).size < 2:
            continue

        result = spearmanr(
            temperature,
            segregation,
            nan_policy="omit",
        )

        if not np.isfinite(result.statistic):
            continue

        rows.append(
            {
                "CATEGORY": category,
                "ID_STORE": id_store,
                "N": n,
                "RHO": float(result.statistic),
                "PVALUE": float(result.pvalue),
            }
        )

    correlations = pl.DataFrame(
        rows,
        schema={
            "CATEGORY": pl.String,
            "ID_STORE": pl.String,
            "N": pl.Int64,
            "RHO": pl.Float64,
            "PVALUE": pl.Float64,
        },
    )

    if correlations.is_empty():
        return correlations.with_columns(
            pl.lit(None, dtype=pl.Float64).alias("QVALUE"),
            pl.lit(False).alias("SIGNIFICANT"),
        )

    # Control the false-discovery rate across all tested POIs.
    _, qvalues, _, _ = multipletests(
        correlations["PVALUE"].to_numpy(),
        alpha=0.05,
        method="fdr_bh",
    )

    return correlations.with_columns(
        pl.Series("QVALUE", qvalues),
    ).with_columns(
        (pl.col("QVALUE") < 0.05).alias("SIGNIFICANT"),
    )


def agg_categories(df: pl.DataFrame, by: str | list[str]) -> pl.DataFrame:
    aggs = [
        pl.len().alias("NUM_POIS"),
        pl.col("SEGREGATION").mean(),
        (
            (pl.col("SEGREGATION") * pl.col("TOTAL_VISITORS")).sum()
            / pl.col("TOTAL_VISITORS").sum()
        ).alias("W_SEGREGATION"),
        pl.col("TOTAL_VISITORS").sum(),
        pl.col("TOTAL_VISITORS").mean().alias("AVG_VISITORS"),
        (
            (pl.col("AVG_DIST") * pl.col("TOTAL_VISITORS")).sum()
            / pl.col("TOTAL_VISITORS").sum()
        ).alias("AVG_DIST"),
    ]

    if "AVG_TMAX" in df.columns:
        aggs.append(pl.col("AVG_TMAX").mean())

    return df.group_by(by).agg(aggs)


if __name__ == "__main__":
    # load and prepare data
    con = db.connect(DB_PATH, read_only=True)

    pois_dim = cache.cached_parquet(
        "pois",
        lambda: data.load_pois(con),
    )
    poi_visits = cache.cached_parquet(
        "static_poi_segregation",
        lambda: data.load_static_poi_segregation(con),
    )
    pois = pois_dim.join(poi_visits, on="ID_STORE")
    categories = agg_categories(pois, ["CATEGORY", "NAICS_TITLE"])

    poi_visits_weekly = cache.cached_parquet(
        "weekly_poi_segregation",
        lambda: data.load_weekly_poi_segregation(con),
    )
    pois_weekly = pois_dim.join(poi_visits_weekly, on="ID_STORE")
    categories_weekly = agg_categories(pois_weekly, ["CATEGORY", "DATE_RANGE_START"])

    # Static segregation
    print("Individual pois")
    print(
        "TOTAL_VISITORS ~ SEGREGATION",
        pois.select(pl.corr("TOTAL_VISITORS", "SEGREGATION", method="spearman"))[0, 0],
    )
    print(
        "AVG_DIST ~ SEGREGATION",
        pois.select(pl.corr("AVG_DIST", "SEGREGATION", method="spearman"))[0, 0],
    )
    print()
    print("Aggregated categories")
    print(
        "TOTAL_VISITORS ~ SEGREGATION",
        categories.select(pl.corr("TOTAL_VISITORS", "SEGREGATION", method="spearman"))[
            0, 0
        ],
    )
    print(
        "AVG_DIST ~ SEGREGATION",
        categories.select(pl.corr("AVG_DIST", "SEGREGATION", method="spearman"))[0, 0],
    )

    fig = plotting.plot_categories(categories)
    figure_path = FIGURE_PATH / "category_segregation.png"
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(figure_path, dpi=400, bbox_inches="tight")

    fig = plotting.plot_poi_map(pois)
    figure_path = FIGURE_PATH / "poi_map.png"
    fig.savefig(figure_path, dpi=400, bbox_inches="tight")

    fig = plotting.plot_relationships(pois)
    figure_path = FIGURE_PATH / "poi_relationships.png"
    fig.savefig(figure_path, dpi=200, bbox_inches="tight")

    fig = plotting.plot_category_counts(categories)
    figure_path = FIGURE_PATH / "category_counts.png"
    fig.savefig(figure_path, dpi=200, bbox_inches="tight")

    fig = plotting.plot_poi_metrics_ccdf(pois)
    figure_path = FIGURE_PATH / "poi_metrics_ccdf.png"
    fig.savefig(figure_path, dpi=200, bbox_inches="tight")

    # Weekly segregation
    rows = []
    for cat in categories_weekly["CATEGORY"].unique():
        X = categories_weekly.filter(pl.col("CATEGORY") == cat)
        corr = spearmanr(X["AVG_TMAX"], X["SEGREGATION"])
        rows.append(
            {
                "CATEGORY": cat,
                "statistic": corr.statistic,  # pyright: ignore[reportAttributeAccessIssue]
                "pvalue": corr.pvalue,  # pyright: ignore[reportAttributeAccessIssue]
            }
        )
    corrs = pl.DataFrame(rows)
    print(corrs)

    poi_correlations = compute_poi_temperature_correlations(
        pois_weekly,
        min_observations=10,
    )

    print(
        poi_correlations.group_by("CATEGORY")
        .agg(
            pl.len().alias("NUM_POIS"),
            pl.col("N").median().alias("MEDIAN_WEEKS"),
            pl.col("RHO").median().alias("MEDIAN_RHO"),
            pl.col("RHO").mean().alias("MEAN_RHO"),
            pl.col("SIGNIFICANT").mean().alias("SHARE_FDR_SIGNIFICANT"),
        )
        .sort("MEDIAN_RHO")
    )

    fig = plotting.plot_poi_temperature_correlations(poi_correlations)
    figure_path = FIGURE_PATH / "poi_temperature_correlations.png"
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    fig.savefig(
        figure_path,
        dpi=300,
        bbox_inches="tight",
    )

    fig = plotting.plot_categories_weekly_linechart(categories_weekly)
    figure_path = FIGURE_PATH / "categories_weekly.png"
    fig.savefig(figure_path, dpi=200, bbox_inches="tight")

    fig = plotting.plot_categories_weekly_scatter(categories_weekly)
    figure_path = FIGURE_PATH / "categories_weekly_scatter.png"
    fig.savefig(figure_path, dpi=200, bbox_inches="tight")

    fig = plotting.plot_tmax_seg_scatter(pois_weekly)
    figure_path = FIGURE_PATH / "tmax_seg_scatter.png"
    fig.savefig(figure_path, dpi=200, bbox_inches="tight")

    # Segregation modeling
    BIN_WIDTH = 2.0
    BIN_ORIGIN = 0.0
    MIN_OBSERVATIONS = 100

    OUTCOME = "SEGREGATION"

    def prepare_data(
        data: pl.DataFrame,
        *,
        bin_width: float,
        bin_origin: float = 0.0,
    ) -> pl.DataFrame:
        """Prepare the shared estimation dataset and assign temperature bins."""
        required = [
            "ID_STORE",
            "CATEGORY",
            OUTCOME,
            "AVG_TMAX",
            "DATE_RANGE_START",
            "CELL_ID",
        ]

        return (
            data.select(required)
            .filter(
                pl.col("ID_STORE").is_not_null(),
                pl.col("CATEGORY").is_not_null(),
                pl.col(OUTCOME).is_finite(),
                pl.col("AVG_TMAX").is_finite(),
                pl.col("DATE_RANGE_START").is_not_null(),
                pl.col("CELL_ID").is_not_null(),
            )
            .with_columns(
                ((pl.col("AVG_TMAX") - bin_origin) / bin_width)
                .floor()
                .cast(pl.Int32)
                .alias("TMAX_BIN_ID")
            )
        )

    def bin_lower(
        bin_id: int | pl.Expr,
        *,
        bin_width: float,
        bin_origin: float,
    ):
        return bin_origin + bin_id * bin_width

    def format_temperature(value: float) -> str:
        return f"{value:g}"

    def fit_temperature_model(
        data: pl.DataFrame,
        *,
        reference_bin_id: int,
        bin_width: float,
        bin_origin: float,
    ) -> tuple[pf.estimation.feols_, pl.DataFrame]:
        """Fit the fixed-effects model and return plot-ready coefficients."""
        pdf = data.to_pandas()

        if reference_bin_id not in pdf["TMAX_BIN_ID"].unique():
            raise ValueError(
                f"Reference bin {reference_bin_id} is absent from the supplied data."
            )

        model = pf.feols(
            f"{OUTCOME} ~ i(TMAX_BIN_ID, ref={reference_bin_id})"
            " | ID_STORE + DATE_RANGE_START",
            data=pdf,
            vcov={"CRV1": "ID_STORE + CELL_ID"},
        )

        coefficients = pl.DataFrame(
            {
                "TERM": model.coef().index.tolist(),
                "ESTIMATE": model.coef().to_numpy(),
                "SE": model.se().to_numpy(),
            }
        )

        effects = (
            coefficients.with_columns(
                pl.col("TERM")
                .str.extract(r"TMAX_BIN_ID::(-?\d+)", 1)
                .cast(pl.Int32)
                .alias("TMAX_BIN_ID")
            )
            .drop_nulls("TMAX_BIN_ID")
            .with_columns(
                (pl.col("ESTIMATE") - 1.96 * pl.col("SE")).alias("CI_LOW"),
                (pl.col("ESTIMATE") + 1.96 * pl.col("SE")).alias("CI_HIGH"),
            )
        )

        reference_effect = pl.DataFrame(
            {
                "TERM": [f"TMAX_BIN_ID::{reference_bin_id}"],
                "ESTIMATE": [0.0],
                "SE": [0.0],
                "TMAX_BIN_ID": [reference_bin_id],
                "CI_LOW": [0.0],
                "CI_HIGH": [0.0],
            },
            schema={
                "TERM": pl.String,
                "ESTIMATE": pl.Float64,
                "SE": pl.Float64,
                "TMAX_BIN_ID": pl.Int32,
                "CI_LOW": pl.Float64,
                "CI_HIGH": pl.Float64,
            },
        )

        effects = (
            pl.concat([effects, reference_effect], how="vertical")
            .unique("TMAX_BIN_ID")
            .sort("TMAX_BIN_ID")
            .with_columns(
                (pl.lit(bin_origin) + pl.col("TMAX_BIN_ID") * bin_width).alias(
                    "BIN_LOW"
                )
            )
            .with_columns(
                (pl.col("BIN_LOW") + bin_width).alias("BIN_HIGH"),
                (pl.col("BIN_LOW") + bin_width / 2).alias("BIN_MIDPOINT"),
            )
        )

        return model, effects

    def add_reference_region(
        ax: plt.Axes,
        *,
        reference_bin_id: int,
        bin_width: float,
        bin_origin: float,
    ) -> None:
        lower = bin_lower(
            reference_bin_id,
            bin_width=bin_width,
            bin_origin=bin_origin,
        )
        upper = lower + bin_width

        ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
        ax.axvspan(
            lower,
            upper,
            color="0.85",
            alpha=0.7,
            label=(
                f"Reference: {format_temperature(lower)}–{format_temperature(upper)}°"
            ),
        )

    def finish_axis(
        ax: plt.Axes,
        *,
        title: str,
        bin_width: float,
    ) -> None:
        ax.set(
            xlabel=f"Average maximum temperature, {bin_width:g}° bin midpoint",
            ylabel="Difference in segregation",
            title=title,
        )
        ax.grid(axis="y", alpha=0.15)
        ax.legend(frameon=False, loc="best")
        sns.despine(ax=ax)

    datalol = prepare_data(
        pois_weekly,
        bin_width=BIN_WIDTH,
        bin_origin=BIN_ORIGIN,
    )

    FIGURE_PATH.mkdir(parents=True, exist_ok=True)

    # Use one global reference bin so category coefficients are comparable.
    reference_bin_id = int(
        datalol.group_by("TMAX_BIN_ID")
        .len()
        .sort("len", descending=True)
        .item(0, "TMAX_BIN_ID")
    )

    reference_low = bin_lower(
        reference_bin_id,
        bin_width=BIN_WIDTH,
        bin_origin=BIN_ORIGIN,
    )
    reference_high = reference_low + BIN_WIDTH

    print(
        f"Shared reference interval: "
        f"{format_temperature(reference_low)}–"
        f"{format_temperature(reference_high)}°"
    )

    # -------------------------------------------------------------------
    # 1. Global model and plot
    # -------------------------------------------------------------------

    print(f"Fitting global model on {datalol.height:,} observations...", flush=True)

    global_model, global_effects = fit_temperature_model(
        datalol,
        reference_bin_id=reference_bin_id,
        bin_width=BIN_WIDTH,
        bin_origin=BIN_ORIGIN,
    )

    global_model.summary()

    global_pdf = global_effects.to_pandas()

    fig, ax = plt.subplots(figsize=(9, 5))

    ax.errorbar(
        global_pdf["BIN_MIDPOINT"],
        global_pdf["ESTIMATE"],
        yerr=[
            global_pdf["ESTIMATE"] - global_pdf["CI_LOW"],
            global_pdf["CI_HIGH"] - global_pdf["ESTIMATE"],
        ],
        fmt="o-",
        color="#0072B2",
        markerfacecolor="white",
        markeredgecolor="#0072B2",
        markersize=5,
        linewidth=1.25,
        elinewidth=0.8,
        capsize=3,
        label="Estimate and 95% CI",
    )

    add_reference_region(
        ax,
        reference_bin_id=reference_bin_id,
        bin_width=BIN_WIDTH,
        bin_origin=BIN_ORIGIN,
    )

    finish_axis(
        ax,
        title="Temperature and segregation",
        bin_width=BIN_WIDTH,
    )

    fig.tight_layout()
    fig.savefig(
        FIGURE_PATH / "temperature_segregation_global.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)

    # -------------------------------------------------------------------
    # 2. All category models in one plot
    # -------------------------------------------------------------------

    category_effects = []

    for category in PALETTE:
        category_data = datalol.filter(pl.col("CATEGORY") == category)

        if category_data.height < MIN_OBSERVATIONS:
            print(f"Skipping {category}: only {category_data.height:,} observations.")
            continue

        available_bins = category_data["TMAX_BIN_ID"].unique().to_list()

        if reference_bin_id not in available_bins:
            print(f"Skipping {category}: shared reference bin is absent.")
            continue

        print(
            f"Fitting {category} on {category_data.height:,} observations...",
            flush=True,
        )

        model, effects = fit_temperature_model(
            category_data,
            reference_bin_id=reference_bin_id,
            bin_width=BIN_WIDTH,
            bin_origin=BIN_ORIGIN,
        )

        effects = effects.with_columns(pl.lit(category).alias("CATEGORY"))
        category_effects.append(effects)

    category_effects = pl.concat(category_effects, how="vertical")

    fig, ax = plt.subplots(figsize=(11, 7))

    for category in PALETTE:
        effects = (
            category_effects.filter(pl.col("CATEGORY") == category)
            .sort("TMAX_BIN_ID")
            .to_pandas()
        )

        if effects.empty:
            continue

        color = PALETTE[category]

        ax.errorbar(
            effects["BIN_MIDPOINT"],
            effects["ESTIMATE"],
            yerr=[
                effects["ESTIMATE"] - effects["CI_LOW"],
                effects["CI_HIGH"] - effects["ESTIMATE"],
            ],
            fmt="o-",
            color=color,
            markerfacecolor="white",
            markeredgecolor=color,
            markersize=3.5,
            linewidth=1.1,
            elinewidth=0.6,
            capsize=2,
            alpha=0.9,
            label=category.replace("_", " "),
        )

    add_reference_region(
        ax,
        reference_bin_id=reference_bin_id,
        bin_width=BIN_WIDTH,
        bin_origin=BIN_ORIGIN,
    )

    finish_axis(
        ax,
        title="Temperature and segregation by POI category",
        bin_width=BIN_WIDTH,
    )

    ax.legend(
        frameon=False,
        loc="upper left",
        bbox_to_anchor=(1.02, 1),
    )

    fig.tight_layout()
    fig.savefig(
        FIGURE_PATH / "temperature_segregation_categories.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)

    # -------------------------------------------------------------------
    # 3. Separate models by CBSA and category
    # -------------------------------------------------------------------

    CBSA_COLUMN = "CBSAFP"

    GRID_CATEGORIES = [category for category in PALETTE if category != "Other"]

    CBSA_MIN_OBSERVATIONS = 100
    CBSA_MIN_TEMPERATURE_BINS = 2

    def prepare_cbsa_data(
        data: pl.DataFrame,
        *,
        cbsa_column: str,
        bin_width: float,
        bin_origin: float = 0.0,
    ) -> pl.DataFrame:
        """
        Prepare data for the CBSA-category models.

        This is separate from prepare_data because prepare_data does not
        retain the CBSA column.
        """
        required = [
            "ID_STORE",
            "CATEGORY",
            OUTCOME,
            "AVG_TMAX",
            "DATE_RANGE_START",
            "CELL_ID",
            cbsa_column,
        ]

        missing_columns = [column for column in required if column not in data.columns]

        if missing_columns:
            raise ValueError(
                f"Missing columns required for CBSA models: {missing_columns}"
            )

        return (
            data.select(required)
            .filter(
                pl.col("ID_STORE").is_not_null(),
                pl.col("CATEGORY").is_not_null(),
                pl.col(OUTCOME).is_finite(),
                pl.col("AVG_TMAX").is_finite(),
                pl.col("DATE_RANGE_START").is_not_null(),
                pl.col("CELL_ID").is_not_null(),
                pl.col(cbsa_column).is_not_null(),
            )
            .with_columns(
                ((pl.col("AVG_TMAX") - bin_origin) / bin_width)
                .floor()
                .cast(pl.Int32)
                .alias("TMAX_BIN_ID")
            )
        )

    def plot_cbsa_category_models(
        data: pl.DataFrame,
        *,
        cbsa_column: str,
        categories: list[str],
        bin_width: float,
        bin_origin: float,
        min_observations: int,
        min_temperature_bins: int = 2,
    ) -> tuple[Figure, pl.DataFrame]:
        """
        Estimate and plot one model for each CBSA-category combination.

        Rows represent CBSAs and columns represent POI categories.
        Each combination uses its own most frequently observed temperature
        bin as the reference category.
        """
        combination_counts = (
            data.filter(pl.col("CATEGORY").is_in(categories))
            .group_by(cbsa_column, "CATEGORY")
            .agg(
                pl.len().alias("N"),
                pl.col("TMAX_BIN_ID").n_unique().alias("NUM_TEMPERATURE_BINS"),
            )
        )

        valid_combinations = combination_counts.filter(
            (pl.col("N") >= min_observations)
            & (pl.col("NUM_TEMPERATURE_BINS") >= min_temperature_bins)
        )

        cbsas = (
            valid_combinations.select(cbsa_column)
            .unique()
            .sort(cbsa_column)
            .get_column(cbsa_column)
            .to_list()
        )

        if not cbsas:
            raise ValueError(
                "No CBSA-category combinations satisfy the minimum "
                "observation and temperature-bin requirements."
            )

        categories = [
            category
            for category in categories
            if valid_combinations.filter(pl.col("CATEGORY") == category).height > 0
        ]

        if not categories:
            raise ValueError("None of the requested categories have valid models.")

        fig, axes = plt.subplots(
            nrows=len(cbsas),
            ncols=len(categories),
            figsize=(
                max(3.2 * len(categories), 10),
                max(2.5 * len(cbsas), 5),
            ),
            sharex=True,
            sharey=True,
            squeeze=False,
            constrained_layout=True,
        )

        all_effects = []

        for row, cbsa in enumerate(cbsas):
            for col, category in enumerate(categories):
                ax = axes[row, col]

                combination = data.filter(
                    (pl.col(cbsa_column) == cbsa) & (pl.col("CATEGORY") == category)
                )

                num_temperature_bins = combination["TMAX_BIN_ID"].n_unique()

                if (
                    combination.height < min_observations
                    or num_temperature_bins < min_temperature_bins
                ):
                    ax.text(
                        0.5,
                        0.5,
                        (
                            "Insufficient data\n"
                            f"n={combination.height:,}\n"
                            f"bins={num_temperature_bins}"
                        ),
                        ha="center",
                        va="center",
                        transform=ax.transAxes,
                        fontsize=8,
                        color="0.45",
                    )

                    ax.set_facecolor("0.97")
                    ax.set_xticks([])
                    ax.set_yticks([])

                    if row == 0:
                        ax.set_title(
                            category.replace("_", " "),
                            fontsize=10,
                        )

                    if col == 0:
                        ax.set_ylabel(
                            str(cbsa),
                            fontsize=9,
                        )

                    continue

                bin_counts = (
                    combination.group_by("TMAX_BIN_ID")
                    .len()
                    .sort(
                        ["len", "TMAX_BIN_ID"],
                        descending=[True, False],
                    )
                )

                reference_bin_id = int(bin_counts.item(0, "TMAX_BIN_ID"))

                print(
                    f"Fitting {cbsa} × {category} on "
                    f"{combination.height:,} observations...",
                    flush=True,
                )

                try:
                    model, effects = fit_temperature_model(
                        combination,
                        reference_bin_id=reference_bin_id,
                        bin_width=bin_width,
                        bin_origin=bin_origin,
                    )
                except Exception as error:
                    print(
                        f"Skipping {cbsa} × {category}: {error}",
                        flush=True,
                    )

                    ax.text(
                        0.5,
                        0.5,
                        "Model failed",
                        ha="center",
                        va="center",
                        transform=ax.transAxes,
                        fontsize=8,
                        color="0.45",
                    )

                    ax.set_facecolor("0.97")
                    ax.set_xticks([])
                    ax.set_yticks([])

                    if row == 0:
                        ax.set_title(
                            category.replace("_", " "),
                            fontsize=10,
                        )

                    if col == 0:
                        ax.set_ylabel(
                            str(cbsa),
                            fontsize=9,
                        )

                    continue

                effects = effects.with_columns(
                    pl.lit(cbsa).alias(cbsa_column),
                    pl.lit(category).alias("CATEGORY"),
                    pl.lit(combination.height).cast(pl.Int64).alias("N"),
                    pl.lit(reference_bin_id).cast(pl.Int32).alias("REFERENCE_BIN_ID"),
                )

                all_effects.append(effects)

                effects_pdf = effects.to_pandas()
                color = PALETTE.get(category, "#4C78A8")

                ax.errorbar(
                    effects_pdf["BIN_MIDPOINT"],
                    effects_pdf["ESTIMATE"],
                    yerr=[
                        (effects_pdf["ESTIMATE"] - effects_pdf["CI_LOW"]),
                        (effects_pdf["CI_HIGH"] - effects_pdf["ESTIMATE"]),
                    ],
                    fmt="o-",
                    color=color,
                    markerfacecolor="white",
                    markeredgecolor=color,
                    markersize=3,
                    linewidth=1,
                    elinewidth=0.6,
                    capsize=2,
                )

                reference_low = bin_lower(
                    reference_bin_id,
                    bin_width=bin_width,
                    bin_origin=bin_origin,
                )

                reference_high = reference_low + bin_width

                ax.axhline(
                    0,
                    color="black",
                    linewidth=0.7,
                    linestyle="--",
                )

                ax.axvspan(
                    reference_low,
                    reference_high,
                    color="0.85",
                    alpha=0.7,
                )

                ax.text(
                    0.98,
                    0.96,
                    (
                        f"n={combination.height:,}\n"
                        f"ref={format_temperature(reference_low)}–"
                        f"{format_temperature(reference_high)}°"
                    ),
                    transform=ax.transAxes,
                    ha="right",
                    va="top",
                    fontsize=6.5,
                    color="0.35",
                )

                ax.grid(
                    axis="y",
                    alpha=0.15,
                )

                sns.despine(ax=ax)

                if row == 0:
                    ax.set_title(
                        category.replace("_", " "),
                        fontsize=10,
                    )

                if col == 0:
                    ax.set_ylabel(
                        f"{cbsa}\nDifference in {OUTCOME.lower()}",
                        fontsize=8,
                    )
                else:
                    ax.set_ylabel("")

                if row == len(cbsas) - 1:
                    ax.set_xlabel(
                        f"Average maximum temperature\n({bin_width:g}° bin midpoint)",
                        fontsize=8,
                    )
                else:
                    ax.set_xlabel("")

                ax.tick_params(
                    axis="both",
                    labelsize=7,
                )

        fig.suptitle(
            (f"Temperature and {OUTCOME.lower()} by CBSA and POI category"),
            fontsize=14,
        )

        if not all_effects:
            return fig, pl.DataFrame()

        return (
            fig,
            pl.concat(
                all_effects,
                how="vertical",
            ),
        )

    cbsa_data = prepare_cbsa_data(
        pois_weekly,
        cbsa_column=CBSA_COLUMN,
        bin_width=BIN_WIDTH,
        bin_origin=BIN_ORIGIN,
    )

    print(
        f"Preparing CBSA-category grid from {cbsa_data.height:,} observations...",
        flush=True,
    )

    cbsa_category_figure, cbsa_category_effects = plot_cbsa_category_models(
        cbsa_data,
        cbsa_column=CBSA_COLUMN,
        categories=GRID_CATEGORIES,
        bin_width=BIN_WIDTH,
        bin_origin=BIN_ORIGIN,
        min_observations=CBSA_MIN_OBSERVATIONS,
        min_temperature_bins=CBSA_MIN_TEMPERATURE_BINS,
    )

    cbsa_category_figure.savefig(
        FIGURE_PATH / "temperature_segregation_cbsa_categories.png",
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(cbsa_category_figure)

    if not cbsa_category_effects.is_empty():
        cbsa_category_effects.write_parquet(
            DATA_PATH / "temperature_segregation_cbsa_category_effects.parquet"
        )

        print(
            "Saved CBSA-category coefficient estimates to "
            f"{DATA_PATH / 'temperature_segregation_cbsa_category_effects.parquet'}"
        )
