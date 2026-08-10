"""The frozen system, serialised for inference outside Python.

WHY THIS EXISTS. The Dataset Lab lets a user analyse their own NCAA prospect
file entirely inside their browser — no upload, no server. To answer with
DraftLens's real numbers rather than an approximation, the browser needs the
frozen estimators themselves. This module writes them out.

WHAT THIS IS NOT. It is not a second model and not a re-fit. Every parameter
here is READ OFF the frozen pipelines built by `board.probability`,
`board.order`, `team_need` and `comparables` — the same objects
`replay.py` and `declared.py` use. Nothing is transcribed by hand, no
hyperparameter is chosen here, and no formula is reimplemented: this module
only calls the frozen code and records what it produced. If a coefficient in
the bundle disagrees with Python, the bundle is wrong, never the reverse.

WHAT IT MUST NEVER CARRY. No draft outcome, no pick, no 2026 result, no
training targets, no per-player training rows. The bundle holds fitted
parameters and peer distributions only, and `assert_no_outcomes` enforces
that on the written bytes.

LAYOUT. One small core file plus one file per NCAA season:

    app/public/data/runtime/core.json          estimators, NBA pool, config
    app/public/data/runtime/season-<YEAR>.json that season's peer references

The season files are large and are fetched only when a user actually imports
a dataset for that season, so the built-in product never pays for them.

    python scripts/build.py app-runtime
"""

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import dataset_format
from paths import CONFIG, ROOT, interim

RUNTIME_DIR = ROOT / "app" / "public" / "data" / "runtime"
CORE_PATH = RUNTIME_DIR / "core.json"

SCHEMA_VERSION = 1

# Seasons a user may import. A season is supported only when every reference
# the frozen pipeline needs exists for it — never by extrapolating a
# neighbouring season onto it.
FIRST_SEASON = 2011
LAST_SEASON = 2026

# Cached extended references (built once, reused by later bundle builds).
TEAM_NEED_EXT = interim("team_need") / "ncaa_percentile_reference_extended.parquet"
COMPARABLE_EXT = interim("comparables") / "ncaa_comparable_reference_extended.parquet"


# ------------------------------------------------------------------ numbers
def _f(x):
    """A JSON-safe float. NaN/inf become null rather than an invalid token."""
    v = float(x)
    return v if np.isfinite(v) else None


def _flist(a):
    return [_f(v) for v in np.asarray(a, dtype="float64")]


def _pack_sorted(values):
    """A sorted float array as little-endian float64 bytes, base64 encoded.

    EXACTNESS IS THE REQUIREMENT, not compactness. The comparables percentile
    is a MID-RANK: a value equal to a reference entry scores half a step
    differently from one just above it. Rounding the reference — at any
    resolution — destroys those equalities for the players who are themselves
    in the reference population, which moves the six-dimension vector and
    therefore the distance to every NBA player. Base64 float64 round-trips
    bit for bit, so the browser ranks against the same numbers Python did.

    Little-endian is assumed on both sides; every platform this runs on is.
    """
    import base64

    v = np.asarray(values, dtype="float64")
    v = np.sort(v[np.isfinite(v)])
    return {"encoding": "f64le-b64", "count": int(v.size),
            "data": base64.b64encode(v.astype("<f8").tobytes()).decode("ascii")}


def _unpack_sorted(packed):
    """The browser-side decoder, mirrored so Python tests can prove agreement."""
    import base64
    return np.frombuffer(base64.b64decode(packed["data"]), dtype="<f8")


# ------------------------------------------------- frozen estimator readout
def _linear_parameters(pipe, feats):
    """Read a fitted sklearn pipeline into plain numbers.

    The pipeline is always ColumnTransformer(numeric: median impute -> standard
    scale, position_3: one-hot) followed by a linear estimator, so its entire
    inference path is: impute, scale, concatenate the one-hot block, dot with
    the coefficients, add the intercept. Everything needed for that is
    extracted here — nothing is assumed or rounded.
    """
    pre = pipe.named_steps["pre"]
    num = pre.named_transformers_["num"]
    pos = pre.named_transformers_["pos"]
    clf = pipe.named_steps["clf"]

    coef = np.asarray(clf.coef_, dtype="float64").ravel()
    intercept = float(np.asarray(clf.intercept_, dtype="float64").ravel()[0])
    categories = [str(c) for c in pos.categories_[0]]

    n_num = len(feats)
    assert len(coef) == n_num + len(categories), (
        f"coefficient vector is {len(coef)} wide; expected {n_num} numeric + "
        f"{len(categories)} one-hot columns")

    return {
        "featureOrder": list(feats),
        "imputerMedians": _flist(num.named_steps["impute"].statistics_),
        "scalerMean": _flist(num.named_steps["scale"].mean_),
        "scalerScale": _flist(num.named_steps["scale"].scale_),
        "positionCategories": categories,
        "coefNumeric": _flist(coef[:n_num]),
        "coefPosition": _flist(coef[n_num:]),
        "intercept": _f(intercept),
    }


def fit_draft_probability():
    """The frozen Draft Probability model, fitted on the approved development
    population — the identical call `replay.fit_draft_probability_2026` makes,
    returning the pipeline instead of predictions."""
    from board.probability import (DRAFT_PROBABILITY, build_pipeline,
                                   feature_set, prepare)
    from data.build import load_development
    from validation import assert_no_holdout, load_fold_config

    dev = load_development()
    assert_no_holdout(dev, "runtime bundle: Draft Probability training")
    feats = feature_set(DRAFT_PROBABILITY["feature_set"], load_fold_config())
    train = prepare(dev, feats)
    pipe = build_pipeline(feats, DRAFT_PROBABILITY["family"],
                          DRAFT_PROBABILITY["class_weight"],
                          {"C": DRAFT_PROBABILITY["C"]})
    pipe.fit(train, train.drafted)
    return pipe, feats


def fit_draft_order():
    """The frozen Draft Order model, plus the train-fold target
    standardisation that `replay.fit_draft_order_2026` inverts."""
    from board.order import DRAFT_ORDER, build_pipeline, draft_sizes, prepare, to_target
    from board.probability import feature_set
    from data.build import load_draft_order
    from validation import assert_no_holdout, load_fold_config

    dev = load_draft_order()
    assert_no_holdout(dev, "runtime bundle: Draft Order training")
    feats = feature_set(DRAFT_ORDER["feature_set"], load_fold_config())
    train = prepare(dev, feats)
    y = to_target(train.pick,
                  train.draft_size if "draft_size" in train
                  else train.draft_year.map(draft_sizes()),
                  DRAFT_ORDER["target"])
    mu, sd = float(np.mean(y)), float(np.std(y))
    sd = sd if sd > 0 else 1.0
    pipe = build_pipeline(feats, DRAFT_ORDER["family"],
                          {"alpha": DRAFT_ORDER["alpha"]})
    pipe.fit(train, (y - mu) / sd)
    return pipe, feats, mu, sd


# --------------------------------------------------------- similarity scale
def similarity_thresholds(reference_distances):
    """Distance cut-points at which the integer similarity score changes.

    `comparables.similarity.similarity_scores` maps a distance to
    `100 * (N - midrank) / N` and the product rounds that to an integer. For a
    distance strictly between two reference values the mid-rank is just the
    count of smaller values, so the whole function collapses to a step
    function with at most 101 steps. Recording those 101 cut-points reproduces
    it exactly while shipping 101 numbers instead of ~160,000.

    `tests/integration/test_runtime_bundle.py` asserts the equivalence against
    the frozen implementation rather than trusting this derivation.
    """
    ref = np.sort(np.asarray(reference_distances, dtype="float64"))
    ref = ref[np.isfinite(ref)]
    n = ref.size
    if n == 0:
        return []
    # score for a query landing in the open interval (ref[k-1], ref[k]) is
    # 100 * (n - k) / n; walk k upward and record where the rounded value drops.
    k = np.arange(n + 1)
    rounded = np.rint(100.0 * (n - k) / n).astype(int)
    cuts = []
    for s in range(100, -1, -1):
        idx = np.flatnonzero(rounded == s)
        # upper distance bound of the band that scores `s`
        cuts.append(_f(ref[min(int(idx[-1]), n - 1)]) if idx.size else None)
    return {"scores": list(range(100, -1, -1)), "upperDistance": cuts,
            "referenceSize": int(n)}


def score_from_thresholds(distance, thresholds):
    """The browser-side lookup, mirrored here so a Python test can prove it
    agrees with `similarity_scores` on real distances."""
    if distance is None or not np.isfinite(distance):
        return None
    cuts = thresholds["upperDistance"]
    scores = thresholds["scores"]
    for s, upper in zip(scores, cuts):
        if upper is not None and distance <= upper:
            return int(s)
    return 0


# ------------------------------------------------------------ core bundle
def build_core():
    """Estimators, frozen configuration and the NBA comparable pool."""
    from board.order import DRAFT_ORDER, draft_sizes
    from board.preprocessing import SEASON_RELATIVE_METRICS
    from board.probability import DRAFT_PROBABILITY
    from board.scoring import GENERAL_BOARD, NEUTRAL_QUALITY
    from comparables.reference import build_ncaa_reference
    from comparables.similarity import (HEIGHT_WINDOWS_INCHES,
                                        MIN_SHARED_COVERAGE, N_COMPARABLES,
                                        build_distance_reference, prepare_pool)
    from comparables.space import DIMENSIONS as CMP_DIMENSIONS
    from comparables.reference import load_pool
    from comparables.space import build_nba_space, build_ncaa_space
    from data.build import load_development
    from team_need.dimensions import CONFIG as TEAM_NEED_CONFIG

    dp_pipe, dp_feats = fit_draft_probability()
    do_pipe, do_feats, do_mu, do_sd = fit_draft_order()

    pool = prepare_pool(load_pool())
    nba_dims, _ = build_nba_space(pool)

    dev = load_development()
    ncaa_ref = _comparable_reference()
    dev_dims, _ = build_ncaa_space(dev, ncaa_ref)
    dist_ref = build_distance_reference(dev_dims, nba_dims, max_prospects=300)

    cmp_dim_names = list(CMP_DIMENSIONS)
    nba_players = []
    for i in range(len(pool)):
        row = pool.iloc[i]
        dims = nba_dims.iloc[i]
        h = pd.to_numeric(pd.Series([row.height_inches]), errors="coerce").iloc[0]
        nba_players.append({
            "id": int(row.athlete_id),
            "name": str(row.athlete_display_name),
            "position": str(row.position_3),
            "heightInches": int(h) if np.isfinite(h) else None,
            "referenceSeasons": [int(s) for s in row.reference_seasons],
            "dimensions": [_f(dims[d]) for d in cmp_dim_names],
        })

    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": ("Frozen DraftLens estimators and peer references, serialised "
                 "for browser-local inference on user-imported datasets. "
                 "Contains no draft outcome, no pick, and no training rows."),
        "supportedSeasons": supported_seasons(),
        "draftSizeByYear": {str(k): int(v) for k, v in draft_sizes().items()},

        "frozen": {
            "draftProbability": dict(DRAFT_PROBABILITY),
            "draftOrder": dict(DRAFT_ORDER),
            "generalBoard": {k: (list(v) if isinstance(v, tuple) else v)
                             for k, v in GENERAL_BOARD.items()},
            "neutralQuality": NEUTRAL_QUALITY,
        },

        "draftProbability": _linear_parameters(dp_pipe, dp_feats),
        "draftOrder": {**_linear_parameters(do_pipe, do_feats),
                       "targetMean": _f(do_mu), "targetStd": _f(do_sd),
                       "target": DRAFT_ORDER["target"]},
        "seasonRelativeMetrics": [m for m in SEASON_RELATIVE_METRICS
                                  if m in dp_feats],

        "teamNeed": {
            "dimensions": TEAM_NEED_CONFIG["dimensions"],
            "profiles": TEAM_NEED_CONFIG["profiles"],
            "reliabilityMinimums": TEAM_NEED_CONFIG["reliability_minimums"],
            "coverage": TEAM_NEED_CONFIG["coverage"],
            "customMode": TEAM_NEED_CONFIG["custom_mode"],
        },

        "datasetFormat": dataset_format.schema(),

        "comparables": {
            "dimensions": {k: {"metrics": v["metrics"], "invert": v["invert"],
                               "kind": v["kind"]}
                           for k, v in CMP_DIMENSIONS.items()},
            "dimensionOrder": cmp_dim_names,
            "nComparables": N_COMPARABLES,
            "minSharedCoverage": MIN_SHARED_COVERAGE,
            "heightWindowsInches": list(HEIGHT_WINDOWS_INCHES),
            "nbaPool": nba_players,
            "similarityThresholds": similarity_thresholds(dist_ref),
        },
    }


# ---------------------------------------------------------- season bundles
def _team_need_reference():
    """The Team Need percentile reference, extended to every supported season.

    The committed 2011-2025 reference used by historical validation is never
    modified; seasons beyond it are appended here exactly as
    `replay.build_2026_team_need` does, and cached so a rebuild is cheap.
    """
    from team_need.reference import build_reference
    if TEAM_NEED_EXT.exists():
        return pd.read_parquet(TEAM_NEED_EXT)
    ref = build_reference(range(FIRST_SEASON, LAST_SEASON + 1))
    TEAM_NEED_EXT.parent.mkdir(parents=True, exist_ok=True)
    ref.to_parquet(TEAM_NEED_EXT, index=False)
    return ref


def _comparable_reference():
    """The NCAA comparables reference, extended to every supported season."""
    from comparables.reference import build_ncaa_reference
    if COMPARABLE_EXT.exists():
        return pd.read_parquet(COMPARABLE_EXT)
    ref = build_ncaa_reference(range(FIRST_SEASON, LAST_SEASON + 1))
    COMPARABLE_EXT.parent.mkdir(parents=True, exist_ok=True)
    ref.to_parquet(COMPARABLE_EXT, index=False)
    return ref


def _season_relative_reference():
    from board.preprocessing import load_reference
    return load_reference()


def supported_seasons():
    """Seasons carrying every reference the frozen pipeline needs.

    A season missing any one of the three references is NOT supported and is
    never served by a neighbouring season's distribution.
    """
    sr = set(int(s) for s in _season_relative_reference().season.unique())
    tn = set(int(s) for s in _team_need_reference().season.unique())
    cp = set(int(s) for s in _comparable_reference().season.unique())
    return sorted(sr & tn & cp)


def build_season(year):
    """Every peer reference one imported season needs."""
    from comparables.space import COMMON_METRICS

    year = int(year)
    out = {"schemaVersion": SCHEMA_VERSION, "season": year}

    # 1. season-relative means/stds for the Draft Probability representation
    sr = _season_relative_reference()
    s = sr[sr.season == year]
    rel = {}
    for pos, g in s.groupby("position_3"):
        rel[str(pos)] = {str(r.metric): {"mean": _f(r["mean"]), "std": _f(r["std"])}
                         for _, r in g.iterrows()}
    out["seasonRelative"] = rel

    # 2. Team Need 101-point quantile grids
    tn = _team_need_reference()
    t = tn[tn.season == year]
    grids = {}
    for (group, metric), g in t.groupby(["reference_group", "metric"]):
        g = g.sort_values("q")
        grids.setdefault(str(group), {})[str(metric)] = {
            "values": _flist(g.value.to_numpy()),
            "n": int(g.n.iloc[0]),
        }
    out["teamNeedGrids"] = grids

    # 3. comparables: the season's NCAA population, sorted per metric. The
    #    percentile is a mid-rank over this exact array, so the whole
    #    distribution ships — a quantile summary would change which NBA
    #    players come back.
    cp = _comparable_reference()
    c = cp[cp.season == year]
    dist = {}
    for m in COMMON_METRICS:
        if m not in c.columns:
            continue
        dist[m] = _pack_sorted(pd.to_numeric(c[m], errors="coerce"))
    out["comparableReference"] = dist
    return out


# ---------------------------------------------------------- parity fixture
PARITY_DIR = ROOT / "tests" / "fixtures" / "parity"


def _engineered_from_dataset(rows, season):
    """An imported dataset -> the engineered feature frame, via the frozen code.

    `build_features` is called directly rather than `engineer_year` because an
    imported file supplies its own team context instead of having it
    reconstructed from hoopR box scores. Everything after that point is the
    untouched frozen implementation.
    """
    from features.basketball import DENOMINATORS, build_features

    d = dataset_format.to_internal_frame(rows, season)
    f = build_features(d).reset_index(drop=True)
    # The denominators travel alongside the ratios exactly as `engineer_year`
    # keeps them: Team Need's reliability rules read them to decide whether a
    # rate rests on enough attempts to mean anything.
    cols = [c for c in DENOMINATORS if c in d.columns]
    keep = pd.concat([
        d[["canonical_prospect_id", "draft_year", "player_name", "college"]],
        d[cols]], axis=1)
    out = pd.concat([keep.reset_index(drop=True), f], axis=1)
    return out.loc[:, ~out.columns.duplicated()]


def score_dataset(rows, season, draft_size):
    """Run the frozen analyses over an imported dataset, in Python.

    This is the reference the browser runtime is held to. It reuses the same
    functions `replay.py` calls, so a difference between this and the product
    board would be a bug in this function, never a second methodology.
    """
    from board.scoring import build_board, rank_board
    from comparables.similarity import (build_distance_reference,
                                        find_comparables, prepare_pool)
    from comparables.reference import load_pool
    from comparables.space import build_nba_space, build_ncaa_space
    from data.build import load_development
    from team_need.dimensions import compute_components, compute_dimensions
    from team_need.profiles import profile_names
    from team_need.reference import PercentileReference
    from team_need.scoring import profile_fit

    feats = _engineered_from_dataset(rows, season)

    dp_pipe, dp_feats = fit_draft_probability()
    do_pipe, do_feats, do_mu, do_sd = fit_draft_order()

    from board.order import DRAFT_ORDER, to_pick
    from board.order import prepare as order_prepare
    from board.probability import prepare as prob_prepare

    p = dp_pipe.predict_proba(prob_prepare(feats, dp_feats))[:, 1]
    y = do_pipe.predict(order_prepare(feats, do_feats)) * do_sd + do_mu
    pick = to_pick(y, np.full(len(feats), draft_size), DRAFT_ORDER["target"])

    board = build_board(p, pick, np.full(len(feats), draft_size))
    board["canonical_prospect_id"] = feats.canonical_prospect_id.to_numpy()
    ranked = rank_board(board)

    reference = PercentileReference(_team_need_reference())
    components, _ = compute_components(feats, reference)
    dims, coverage = compute_dimensions(feats, reference, components)
    profiles = {name: profile_fit(feats, name, reference, components, dims,
                                  coverage)
                for name in profile_names()}

    pool = prepare_pool(load_pool())
    nba_dims, _ = build_nba_space(pool)
    ncaa_ref = _comparable_reference()
    dev_dims, _ = build_ncaa_space(load_development(), ncaa_ref)
    dist_ref = build_distance_reference(dev_dims, nba_dims, max_prospects=300)
    ncaa_dims, _ = build_ncaa_space(feats, ncaa_ref)

    comparables = {}
    for i in range(len(feats)):
        pid = str(feats.canonical_prospect_id.iloc[i])
        comparables[pid] = find_comparables(
            ncaa_dims.iloc[i], pool, nba_dims,
            prospect_name=None, distance_reference=dist_ref,
            prospect_height=feats.height.iloc[i])

    return {"features": feats, "probability": p, "orderPick": pick,
            "board": board, "ranked": ranked, "dimensions": dims,
            "profiles": profiles, "comparables": comparables}


def build_parity_fixture(year=2026):
    """A DraftLens-format dataset built from real NCAA inputs, plus the frozen
    Python answers for it.

    The browser runtime must reproduce these exactly before imported datasets
    are allowed a General Board. Carries no draft outcome: the inputs are
    box-score totals and the answers are pre-draft analyses.
    """
    from data.build import raw_prospect_features
    from data.matching import load_overrides, season_index
    from data.population import load_declared
    from features.basketball import team_context, to_position_3

    declared = load_declared(year)
    matched, raw, _, _ = raw_prospect_features(
        year, declared, season_index(year), load_overrides())
    ids = set(pd.to_numeric(raw.hoopr_athlete_id, errors="coerce")
              .dropna().astype("int64"))
    ctx = team_context(year, ids)
    ctx["athlete_id"] = ctx.athlete_id.astype("int64")
    raw = raw.copy()
    raw["_aid"] = pd.to_numeric(raw.hoopr_athlete_id, errors="coerce")
    d = raw.merge(ctx.rename(columns={"athlete_id": "_aid"}), on="_aid",
                  how="left").reset_index(drop=True)
    d = d[d.hoopr_athlete_id.notna() & d.games_played.notna()].reset_index(
        drop=True)
    d = d.sort_values("canonical_prospect_id").reset_index(drop=True)

    def val(row, col):
        if col not in d.columns:
            return None
        v = row[col]
        if isinstance(v, str):
            return v
        v = pd.to_numeric(pd.Series([v]), errors="coerce").iloc[0]
        return None if not np.isfinite(v) else (
            int(v) if float(v).is_integer() else float(v))

    rows = []
    for _, r in d.iterrows():
        row = {
            "prospect_id": str(r.canonical_prospect_id),
            "name": str(r.player_name),
            "school": str(r.college) if pd.notna(r.college) else None,
            "position": to_position_3(r.get("hoopr_position")),
        }
        for f in dataset_format.PROSPECT_FIELDS:
            name = f["name"]
            if name in row:
                continue
            row[name] = val(r, dataset_format.TO_PRIMITIVE.get(name, name))
        rows.append(row)

    from board.order import draft_sizes
    size = draft_sizes()[year]
    dataset = {
        "schemaVersion": dataset_format.SCHEMA_VERSION,
        "metadata": {
            "dataset_name": f"DraftLens {year} parity fixture",
            "season": year,
            "population_type": dataset_format.FULL_BOARD_POPULATION,
            "draft_size": size,
        },
        "prospects": rows,
    }

    scored = score_dataset(rows, year, size)
    ranked = scored["ranked"]
    dims = scored["dimensions"]
    expected = {
        "season": year,
        "draftSize": size,
        "prospects": [],
    }
    order = {pid: i for i, pid in enumerate(ranked.canonical_prospect_id)}
    for i, pid in enumerate(scored["features"].canonical_prospect_id):
        pid = str(pid)
        cmp_entry = scored["comparables"][pid]
        expected["prospects"].append({
            "prospectId": pid,
            "draftProbability": _f(scored["probability"][i]),
            "draftOrderPick": _f(scored["orderPick"][i]),
            "stageBQuality": _f(scored["board"].stage_b_quality.iloc[i]),
            "boardSignal": _f(scored["board"].final_board_signal.iloc[i]),
            "overallScore": int(scored["board"].overall_score.iloc[i]),
            "boardRank": int(ranked.board_rank.iloc[order[pid]]),
            "dimensions": {k.lower(): _f(dims[k].iloc[i]) for k in dims.columns},
            "profiles": {name.lower(): {
                "fitRaw": _f(p.fit_raw.iloc[i]),
                "fitScore": _f(p.fit_score.iloc[i]),
                "eligibility": str(p.eligibility_status.iloc[i]),
                "status": str(p.status.iloc[i]),
            } for name, p in scored["profiles"].items()},
            "comparables": {
                "status": cmp_entry["status"],
                "heightWindowInches": cmp_entry.get("height_window_inches"),
                "players": [{"id": c["nba_player_id"],
                             "rank": c["rank"],
                             "similarityScore": c["similarity_score"],
                             "rawDistance": c["raw_distance"]}
                            for c in cmp_entry["comparables"]],
            },
        })
    return dataset, expected


def write_parity_fixture(year=2026, directory=PARITY_DIR, log=print):
    directory.mkdir(parents=True, exist_ok=True)
    dataset, expected = build_parity_fixture(year)
    for name, payload in (("dataset", dataset), ("expected", expected)):
        assert_no_outcomes(payload, f"parity {name} fixture")
        text = json.dumps(payload, indent=1, sort_keys=True)
        (directory / f"{name}_{year}.json").write_text(text)
        log(f"  {name}_{year}.json  {len(text) / 1024:>7.0f} KB")
    return dataset, expected


# ------------------------------------------------------------------ guards
PROHIBITED_SUBSTRINGS = (
    "actual_pick", "actualpick", "draft_team", "draftteam", "actual_round",
    "\"drafted\"", "\"pick\"", "was_drafted", "career_",
)


def assert_no_outcomes(payload, label):
    """The bundle must carry parameters and peer distributions only.

    The import schema legitimately NAMES the outcome columns it refuses, so
    those two lists are lifted out before scanning. They are the specification
    of what is banned, not an instance of it — everything else, including
    every number, still has to be clean.
    """
    if isinstance(payload, str):
        scanned = payload
    else:
        clone = json.loads(json.dumps(payload, default=str))
        fmt = clone.get("datasetFormat")
        if isinstance(fmt, dict):
            fmt.pop("prohibitedFields", None)
            fmt.pop("derivedRateFields", None)
        scanned = json.dumps(clone, sort_keys=True)

    low = scanned.lower()
    for bad in PROHIBITED_SUBSTRINGS:
        assert bad not in low, f"{label} contains prohibited token {bad!r}"
    return True


# ------------------------------------------------------------------- write
def write_bundle(directory=RUNTIME_DIR, seasons=None, log=print):
    """Write the core bundle and one file per supported season."""
    directory.mkdir(parents=True, exist_ok=True)
    core = build_core()
    seasons = [int(s) for s in (seasons if seasons is not None
                                else core["supportedSeasons"])]

    assert_no_outcomes(core, "runtime core bundle")
    text = json.dumps(core, separators=(",", ":"), sort_keys=True)
    CORE_PATH.write_text(text)
    log(f"  core.json  {len(text) / 1024:>8.0f} KB  "
        f"{len(core['comparables']['nbaPool'])} NBA reference players")

    written = [CORE_PATH]
    for year in seasons:
        payload = build_season(year)
        assert_no_outcomes(payload, f"runtime season bundle {year}")
        t = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        p = directory / f"season-{year}.json"
        p.write_text(t)
        written.append(p)
        log(f"  season-{year}.json  {len(t) / 1024:>8.0f} KB")
    return written
