use anyhow::{bail, Context, Result};
use clap::{Parser, ValueEnum};
use csv::{ReaderBuilder, StringRecord};
use std::collections::HashMap;
use std::io;

const EARTH_RADIUS_M: f64 = 6_371_008.8;

#[derive(Parser, Debug)]
#[command(
    name = "morans-i",
    about = "Compute global Moran's I using distance-band weights"
)]
struct Args {
    /// Maximum neighbor distance in meters
    #[arg(long)]
    threshold: f64,

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
    Binary,
    RowStandardized,
}

#[derive(Clone, Copy, Debug, ValueEnum)]
enum IslandStrategy {
    Keep,
    Exclude,
    Error,
}

#[derive(Clone, Copy, Debug, ValueEnum)]
enum InvalidStrategy {
    Error,
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
    let args = Args::parse();

    if !args.threshold.is_finite() || args.threshold <= 0.0 {
        bail!("threshold must be a positive finite number");
    }

    let mut reader = ReaderBuilder::new()
        .has_headers(true)
        .from_reader(io::stdin());

    let headers = reader.headers()?.clone();

    let lon_index = column_index(&headers, &args.lon)?;
    let lat_index = column_index(&headers, &args.lat)?;
    let value_index = column_index(&headers, &args.value)?;

    // Angular cell size corresponding to the distance threshold.
    // Haversine distance is still used for the final neighbor test.
    let cell_size_rad = args.threshold / EARTH_RADIUS_M;

    let mut points = Vec::new();
    let mut skipped_rows = 0usize;
    let mut max_abs_lat = 0.0_f64;

    for (row_number, result) in reader.records().enumerate() {
        let record = result.with_context(|| {
            format!("failed to read CSV row {}", row_number + 2)
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
                        .with_context(|| format!("invalid CSV row {}", row_number + 2));
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

    let mut grid: HashMap<(i32, i32), Vec<usize>> = HashMap::new();

    for (index, point) in points.iter().enumerate() {
        grid.entry(point.cell).or_default().push(index);
    }

    /*
    Longitude degrees represent shorter distances at higher latitudes.
    Searching this many longitude cells ensures that all candidate
    neighbors are considered within a US metropolitan area.
    */
    let cos_max_lat = max_abs_lat.cos().max(1e-6);
    let lon_cell_reach = (1.0 / cos_max_lat).ceil() as i32;

    let mut degrees = vec![0_u64; points.len()];
    let mut neighbor_pairs = 0_u64;

    visit_neighbor_pairs(
        &points,
        &grid,
        args.threshold,
        lon_cell_reach,
        |i, j| {
            degrees[i] += 1;
            degrees[j] += 1;
            neighbor_pairs += 1;
        },
    );

    let island_count = degrees.iter().filter(|&&degree| degree == 0).count();

    if island_count > 0 {
        match args.islands {
            IslandStrategy::Error => {
                bail!(
                    "{} observations have no neighbors within {} meters",
                    island_count,
                    args.threshold
                );
            }
            IslandStrategy::Keep | IslandStrategy::Exclude => {
                eprintln!(
                    "warning: {} observations have no neighbors",
                    island_count
                );
            }
        }
    }

    let active = |index: usize| {
        !matches!(args.islands, IslandStrategy::Exclude) || degrees[index] > 0
    };

    let active_count = (0..points.len()).filter(|&i| active(i)).count();

    if active_count < 2 {
        bail!("fewer than two observations remain after handling islands");
    }

    if neighbor_pairs == 0 {
        bail!("no neighbor pairs found within the specified threshold");
    }

    let mean = points
        .iter()
        .enumerate()
        .filter(|(i, _)| active(*i))
        .map(|(_, point)| point.value)
        .sum::<f64>()
        / active_count as f64;

    let deviations: Vec<f64> = points
        .iter()
        .map(|point| point.value - mean)
        .collect();

    let denominator = deviations
        .iter()
        .enumerate()
        .filter(|(i, _)| active(*i))
        .map(|(_, deviation)| deviation * deviation)
        .sum::<f64>();

    if denominator <= f64::EPSILON {
        bail!("Moran's I is undefined because the variable has zero variance");
    }

    let mut numerator = 0.0_f64;

    visit_neighbor_pairs(
        &points,
        &grid,
        args.threshold,
        lon_cell_reach,
        |i, j| {
            let product = deviations[i] * deviations[j];

            match args.transform {
                Transform::Binary => {
                    // Each undirected pair represents w_ij and w_ji.
                    numerator += 2.0 * product;
                }
                Transform::RowStandardized => {
                    numerator += product
                        * (1.0 / degrees[i] as f64 + 1.0 / degrees[j] as f64);
                }
            }
        },
    );

    let weight_sum = match args.transform {
        Transform::Binary => 2.0 * neighbor_pairs as f64,
        Transform::RowStandardized => {
            // Each non-island row sums to one.
            degrees.iter().filter(|&&degree| degree > 0).count() as f64
        }
    };

    let morans_i =
        (active_count as f64 / weight_sum) * (numerator / denominator);

    println!("{{");
    println!("  \"morans_i\": {},", morans_i);
    println!("  \"observations\": {},", active_count);
    println!("  \"input_observations\": {},", points.len());
    println!("  \"islands\": {},", island_count);
    println!("  \"neighbor_pairs\": {},", neighbor_pairs);
    println!("  \"threshold_m\": {},", args.threshold);
    println!(
        "  \"transform\": \"{}\",",
        match args.transform {
            Transform::Binary => "binary",
            Transform::RowStandardized => "row-standardized",
        }
    );
    println!(
        "  \"island_strategy\": \"{}\",",
        match args.islands {
            IslandStrategy::Keep => "keep",
            IslandStrategy::Exclude => "exclude",
            IslandStrategy::Error => "error",
        }
    );
    println!("  \"skipped_rows\": {}", skipped_rows);
    println!("}}");

    Ok(())
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

    let lat_cell = ((lat_rad + std::f64::consts::FRAC_PI_2) / cell_size_rad)
        .floor() as i32;

    let lon_cell = ((lon_rad + std::f64::consts::PI) / cell_size_rad)
        .floor() as i32;

    Ok(Point {
        lon_rad,
        lat_rad,
        value,
        cell: (lat_cell, lon_cell),
    })
}

fn parse_field(record: &StringRecord, index: usize, name: &str) -> Result<f64> {
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
    F: FnMut(usize, usize),
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
                    // Avoid self-neighbors and process each pair once.
                    if j <= i {
                        continue;
                    }

                    let distance = haversine_m(point, &points[j]);

                    if distance <= threshold_m {
                        visit(i, j);
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

    let central_angle = 2.0 * haversine.sqrt().asin();

    EARTH_RADIUS_M * central_angle
}
