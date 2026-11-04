use anyhow::{bail, Context, Result};
use clap::{Parser, ValueEnum};
use csv::{ReaderBuilder, StringRecord};
use std::collections::HashMap;
use std::io;

const EARTH_RADIUS_M: f64 = 6_371_008.8;

#[derive(Parser, Debug)]
#[command(
    name = "morans-i",
    version,
    about = "Compute global Moran's I using distance-band spatial weights"
)]
struct Args {
    /// Distance thresholds in meters.
    ///
    /// Examples:
    ///   --thresholds 10
    ///   --thresholds 10,100,1000
    ///   --thresholds 10 100 1000
    ///
    /// --threshold is accepted as an alias.
    #[arg(
        long = "thresholds",
        visible_alias = "threshold",
        value_delimiter = ',',
        num_args = 1..
    )]
    thresholds: Vec<f64>,

    /// Name of the longitude column
    #[arg(long, default_value = "lon")]
    lon: String,

    /// Name of the latitude column
    #[arg(long, default_value = "lat")]
    lat: String,

    /// Name of the variable-of-interest column
    #[arg(long, default_value = "value")]
    value: String,

    /// Weight transformation
    #[arg(long, value_enum, default_value_t = Transform::Binary)]
    transform: Transform,

    /// How to handle observations without neighbors
    #[arg(long, value_enum, default_value_t = IslandStrategy::Keep)]
    islands: IslandStrategy,

    /// How to handle invalid CSV rows
    #[arg(long, value_enum, default_value_t = InvalidStrategy::Error)]
    invalid: InvalidStrategy,
}

#[derive(Clone, Copy, Debug, ValueEnum)]
enum Transform {
    /// wij = 1 when dij <= threshold
    Binary,

    /// Binary weights divided by each observation's neighbor count
    RowStandardized,
}

#[derive(Clone, Copy, Debug, ValueEnum)]
enum IslandStrategy {
    /// Keep islands in n, the mean, and the variance
    Keep,

    /// Exclude islands and recompute the mean and variance
    Exclude,

    /// Return an error if any islands are found
    Error,
}

#[derive(Clone, Copy, Debug, ValueEnum)]
enum InvalidStrategy {
    /// Return an error for an invalid row
    Error,

    /// Skip invalid rows
    Skip,
}

#[derive(Debug)]
struct Point {
    lon_rad: f64,
    lat_rad: f64,
    value: f64,
    cell: (i32, i32),
}

fn main() -> Result<()> {
    let mut args = Args::parse();

    validate_thresholds(&args.thresholds)?;

    args.thresholds.sort_by(f64::total_cmp);
    args.thresholds.dedup_by(|a, b| a.total_cmp(b).is_eq());

    let threshold_count = args.thresholds.len();
    let max_threshold = *args
        .thresholds
        .last()
        .context("at least one threshold is required")?;

    let mut reader = ReaderBuilder::new()
        .has_headers(true)
        .from_reader(io::stdin());

    let headers = reader.headers()?.clone();

    let lon_index = column_index(&headers, &args.lon)?;
    let lat_index = column_index(&headers, &args.lat)?;
    let value_index = column_index(&headers, &args.value)?;

    /*
    The grid is built using the largest threshold. Smaller thresholds
    reuse candidate pairs found using this grid.
    */
    let cell_size_rad = max_threshold / EARTH_RADIUS_M;

    let mut points = Vec::new();
    let mut skipped_rows = 0usize;
    let mut max_abs_lat = 0.0_f64;

    for (row_index, result) in reader.records().enumerate() {
        let row_number = row_index + 2;

        let record = result.with_context(|| {
            format!("failed to read CSV row {row_number}")
        })?;

        match parse_point(
            &record,
            lon_index,
            lat_index,
            value_index,
            cell_size_rad,
        ) {
            Ok(point) => {
                max_abs_lat = max_abs_lat.max(point.lat_rad.abs());
                points.push(point);
            }
            Err(error) => match args.invalid {
                InvalidStrategy::Error => {
                    return Err(error)
                        .with_context(|| format!("invalid CSV row {row_number}"));
                }
                InvalidStrategy::Skip => {
                    skipped_rows += 1;
                }
            },
        }
    }

    if points.len() < 2 {
        bail!("at least two valid observations are required");
    }

    let grid = build_grid(&points);

    /*
    Longitude distances shrink with latitude. This determines how many
    longitude cells must be inspected to avoid missing neighbors.
    */
    let cos_max_lat = max_abs_lat.cos().max(1e-6);
    let lon_cell_reach = (1.0 / cos_max_lat).ceil() as i32;

    /*
    degrees[t][i] contains the number of neighbors of observation i
    under threshold t.
    */
    let mut degrees = vec![vec![0_u64; points.len()]; threshold_count];
    let mut neighbor_pairs = vec![0_u64; threshold_count];

    /*
    First scan:
      - count neighbors
      - count undirected neighbor pairs
    */
    visit_neighbor_pairs(
        &points,
        &grid,
        max_threshold,
        lon_cell_reach,
        |i, j, distance| {
            let first_threshold = args
                .thresholds
                .partition_point(|threshold| *threshold < distance);

            for threshold_index in first_threshold..threshold_count {
                degrees[threshold_index][i] += 1;
                degrees[threshold_index][j] += 1;
                neighbor_pairs[threshold_index] += 1;
            }
        },
    );

    let mut means = vec![0.0_f64; threshold_count];
    let mut denominators = vec![0.0_f64; threshold_count];
    let mut active_counts = vec![0usize; threshold_count];
    let mut island_counts = vec![0usize; threshold_count];

    for threshold_index in 0..threshold_count {
        let threshold = args.thresholds[threshold_index];
        let threshold_degrees = &degrees[threshold_index];

        let island_count = threshold_degrees
            .iter()
            .filter(|&&degree| degree == 0)
            .count();

        island_counts[threshold_index] = island_count;

        if island_count > 0 {
            match args.islands {
                IslandStrategy::Error => {
                    bail!(
                        "{} observations have no neighbors within {} meters",
                        island_count,
                        threshold
                    );
                }
                IslandStrategy::Keep | IslandStrategy::Exclude => {
                    eprintln!(
                        "warning: {} observations have no neighbors within {} meters",
                        island_count,
                        threshold
                    );
                }
            }
        }

        let active_count = match args.islands {
            IslandStrategy::Exclude => {
                threshold_degrees
                    .iter()
                    .filter(|&&degree| degree > 0)
                    .count()
            }
            IslandStrategy::Keep | IslandStrategy::Error => points.len(),
        };

        active_counts[threshold_index] = active_count;

        if active_count < 2 || neighbor_pairs[threshold_index] == 0 {
            continue;
        }

        let mean = points
            .iter()
            .enumerate()
            .filter(|(index, _)| {
                is_active(
                    *index,
                    threshold_degrees,
                    args.islands,
                )
            })
            .map(|(_, point)| point.value)
            .sum::<f64>()
            / active_count as f64;

        means[threshold_index] = mean;

        denominators[threshold_index] = points
            .iter()
            .enumerate()
            .filter(|(index, _)| {
                is_active(
                    *index,
                    threshold_degrees,
                    args.islands,
                )
            })
            .map(|(_, point)| {
                let deviation = point.value - mean;
                deviation * deviation
            })
            .sum::<f64>();
    }

    let mut numerators = vec![0.0_f64; threshold_count];

    /*
    Second scan:
      - calculate Moran's I numerator

    Neighbor pairs are recomputed rather than stored, keeping memory
    usage proportional to observations times thresholds.
    */
    visit_neighbor_pairs(
        &points,
        &grid,
        max_threshold,
        lon_cell_reach,
        |i, j, distance| {
            let first_threshold = args
                .thresholds
                .partition_point(|threshold| *threshold < distance);

            for threshold_index in first_threshold..threshold_count {
                if active_counts[threshold_index] < 2 {
                    continue;
                }

                let mean = means[threshold_index];

                let product =
                    (points[i].value - mean) * (points[j].value - mean);

                match args.transform {
                    Transform::Binary => {
                        /*
                        Each undirected pair represents both wij and wji.
                        */
                        numerators[threshold_index] += 2.0 * product;
                    }
                    Transform::RowStandardized => {
                        let degree_i =
                            degrees[threshold_index][i] as f64;

                        let degree_j =
                            degrees[threshold_index][j] as f64;

                        numerators[threshold_index] += product
                            * (1.0 / degree_i + 1.0 / degree_j);
                    }
                }
            }
        },
    );

    print_results(
        &args,
        &points,
        skipped_rows,
        &degrees,
        &neighbor_pairs,
        &island_counts,
        &active_counts,
        &denominators,
        &numerators,
    );

    Ok(())
}

fn validate_thresholds(thresholds: &[f64]) -> Result<()> {
    if thresholds.is_empty() {
        bail!("at least one threshold is required");
    }

    for &threshold in thresholds {
        if !threshold.is_finite() || threshold <= 0.0 {
            bail!(
                "thresholds must be positive finite numbers; received {}",
                threshold
            );
        }
    }

    Ok(())
}

fn build_grid(points: &[Point]) -> HashMap<(i32, i32), Vec<usize>> {
    let mut grid: HashMap<(i32, i32), Vec<usize>> = HashMap::new();

    for (index, point) in points.iter().enumerate() {
        grid.entry(point.cell).or_default().push(index);
    }

    grid
}

fn is_active(
    index: usize,
    degrees: &[u64],
    island_strategy: IslandStrategy,
) -> bool {
    match island_strategy {
        IslandStrategy::Exclude => degrees[index] > 0,
        IslandStrategy::Keep | IslandStrategy::Error => true,
    }
}

fn column_index(headers: &StringRecord, name: &str) -> Result<usize> {
    headers
        .iter()
        .position(|header| header == name)
        .with_context(|| format!("CSV column '{name}' was not found"))
}

fn parse_point(
    record: &StringRecord,
    lon_index: usize,
    lat_index: usize,
    value_index: usize,
    cell_size_rad: f64,
) -> Result<Point> {
    let lon = parse_field(record, lon_index, "longitude")?;
    let lat = parse_field(record, lat_index, "latitude")?;
    let value = parse_field(record, value_index, "value")?;

    if !(-180.0..=180.0).contains(&lon) {
        bail!("longitude must be between -180 and 180");
    }

    if !(-90.0..=90.0).contains(&lat) {
        bail!("latitude must be between -90 and 90");
    }

    let lon_rad = lon.to_radians();
    let lat_rad = lat.to_radians();

    let lat_cell =
        ((lat_rad + std::f64::consts::FRAC_PI_2) / cell_size_rad)
            .floor() as i32;

    let lon_cell =
        ((lon_rad + std::f64::consts::PI) / cell_size_rad)
            .floor() as i32;

    Ok(Point {
        lon_rad,
        lat_rad,
        value,
        cell: (lat_cell, lon_cell),
    })
}

fn parse_field(
    record: &StringRecord,
    index: usize,
    name: &str,
) -> Result<f64> {
    let raw = record
        .get(index)
        .with_context(|| format!("missing {name} field"))?;

    let value: f64 = raw
        .parse()
        .with_context(|| format!("invalid {name}: '{raw}'"))?;

    if !value.is_finite() {
        bail!("{name} must be finite");
    }

    Ok(value)
}

fn visit_neighbor_pairs<F>(
    points: &[Point],
    grid: &HashMap<(i32, i32), Vec<usize>>,
    threshold_m: f64,
    lon_cell_reach: i32,
    mut visit: F,
) where
    F: FnMut(usize, usize, f64),
{
    for (i, point) in points.iter().enumerate() {
        let (lat_cell, lon_cell) = point.cell;

        for lat_offset in -1..=1 {
            for lon_offset in -lon_cell_reach..=lon_cell_reach {
                let candidate_cell = (
                    lat_cell + lat_offset,
                    lon_cell + lon_offset,
                );

                let Some(candidates) = grid.get(&candidate_cell) else {
                    continue;
                };

                for &j in candidates {
                    /*
                    Exclude self-neighbors and process each pair once.
                    Distinct rows with identical coordinates remain
                    valid neighbors.
                    */
                    if j <= i {
                        continue;
                    }

                    let distance = haversine_m(point, &points[j]);

                    if distance <= threshold_m {
                        visit(i, j, distance);
                    }
                }
            }
        }
    }
}

fn haversine_m(a: &Point, b: &Point) -> f64 {
    let delta_lat = b.lat_rad - a.lat_rad;
    let delta_lon = b.lon_rad - a.lon_rad;

    let sin_lat = (delta_lat / 2.0).sin();
    let sin_lon = (delta_lon / 2.0).sin();

    let haversine = sin_lat * sin_lat
        + a.lat_rad.cos() * b.lat_rad.cos() * sin_lon * sin_lon;

    /*
    Clamp to protect against small floating-point errors that could
    otherwise produce asin values slightly outside its valid domain.
    */
    let haversine = haversine.clamp(0.0, 1.0);
    let central_angle = 2.0 * haversine.sqrt().asin();

    EARTH_RADIUS_M * central_angle
}

#[allow(clippy::too_many_arguments)]
fn print_results(
    args: &Args,
    points: &[Point],
    skipped_rows: usize,
    degrees: &[Vec<u64>],
    neighbor_pairs: &[u64],
    island_counts: &[usize],
    active_counts: &[usize],
    denominators: &[f64],
    numerators: &[f64],
) {
    println!("[");

    for threshold_index in 0..args.thresholds.len() {
        let active_count = active_counts[threshold_index];
        let pairs = neighbor_pairs[threshold_index];
        let denominator = denominators[threshold_index];

        let weight_sum = match args.transform {
            Transform::Binary => 2.0 * pairs as f64,

            /*
            Every non-island row sums to one after row standardization.
            */
            Transform::RowStandardized => degrees[threshold_index]
                .iter()
                .filter(|&&degree| degree > 0)
                .count() as f64,
        };

        let morans_i = if active_count < 2
            || pairs == 0
            || weight_sum == 0.0
            || denominator <= f64::EPSILON
        {
            None
        } else {
            Some(
                (active_count as f64 / weight_sum)
                    * (numerators[threshold_index] / denominator),
            )
        };

        println!("  {{");
        println!(
            "    \"threshold_m\": {},",
            args.thresholds[threshold_index]
        );

        match morans_i {
            Some(value) => {
                println!("    \"morans_i\": {},", value);
            }
            None => {
                println!("    \"morans_i\": null,");
            }
        }

        println!("    \"observations\": {},", active_count);
        println!("    \"input_observations\": {},", points.len());
        println!(
            "    \"islands\": {},",
            island_counts[threshold_index]
        );
        println!("    \"neighbor_pairs\": {},", pairs);
        println!("    \"weight_sum\": {},", weight_sum);

        println!(
            "    \"transform\": \"{}\",",
            match args.transform {
                Transform::Binary => "binary",
                Transform::RowStandardized => "row-standardized",
            }
        );

        println!(
            "    \"island_strategy\": \"{}\",",
            match args.islands {
                IslandStrategy::Keep => "keep",
                IslandStrategy::Exclude => "exclude",
                IslandStrategy::Error => "error",
            }
        );

        println!("    \"skipped_rows\": {}", skipped_rows);

        if threshold_index + 1 == args.thresholds.len() {
            println!("  }}");
        } else {
            println!("  }},");
        }
    }

    println!("]");
}
