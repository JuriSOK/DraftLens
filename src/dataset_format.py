"""DraftLens Dataset Format v1 — the contract for an imported prospect file.

A user can bring their own NCAA class and receive the frozen DraftLens
analyses. That only works if the file says exactly what DraftLens needs, in
units it can trust, so this module is the ONE place the format is defined.
The schema is written into the runtime bundle and the browser validates
against it; nothing about the format is retyped in TypeScript.

THREE DESIGN RULES, each closing a way an import could quietly go wrong:

  COUNTS, NEVER RATES. Every input is a season TOTAL or a physical
  measurement. DraftLens derives each percentage itself with the same formula
  it uses for its own data. This is what removes the "is 41.2 a percent or is
  0.412" ambiguity at the root rather than guessing at it per column: a
  three-point percentage is never an input, so it can never arrive in the
  wrong unit.

  MISSING IS A CAPABILITY QUESTION, NOT A GAP TO FILL. Optional groups
  (team context, shot profile) unlock specific analyses. Their absence is
  reported as reduced capability and reaches the model as the frozen
  train-median imputation — never as a fabricated value.

  OUTCOMES ARE REFUSED. Imported analysis is pre-draft. A column naming what
  actually happened is rejected, not ignored, because a file carrying one is
  a file whose author may expect it to be used.

The unit conventions are deliberately narrow and are all stated in the
template: total minutes (not per game), inches, pounds, integer counts, and a
season expressed as the year the NCAA season ends (2026 = the 2025-26 season).
"""

SCHEMA_VERSION = 1

POSITIONS = ["G", "F", "C", "UNKNOWN"]

# Which population the file describes. Draft Probability and Draft Order were
# validated on final NCAA early entrants; a file that is not that population
# is not eligible for a General Board, and no substitute number is offered.
POPULATION_TYPES = {
    "ncaa_early_entry": "NCAA players who declared for this draft — the "
                        "population DraftLens's draft models were validated "
                        "on.",
    "ncaa_all_players": "Any NCAA players, not a declared-entrant class.",
    "other": "Any other population.",
}
FULL_BOARD_POPULATION = "ncaa_early_entry"


def _f(name, group, required, kind, unit, description, minimum=None,
       maximum=None, integer=False):
    return {"name": name, "group": group, "required": required, "type": kind,
            "unit": unit, "description": description, "min": minimum,
            "max": maximum, "integer": integer}


# --------------------------------------------------------------- metadata
METADATA_FIELDS = [
    _f("schema_version", "metadata", True, "integer", "—",
       f"Must be {SCHEMA_VERSION}.", minimum=SCHEMA_VERSION,
       maximum=SCHEMA_VERSION, integer=True),
    _f("dataset_name", "metadata", True, "string", "—",
       "A name for this class, shown throughout the analysis."),
    _f("season", "metadata", True, "integer", "year",
       "The year the NCAA season ENDS: 2026 means the 2025-26 season. Must "
       "be a season DraftLens has peer references for.",
       minimum=1900, maximum=2100, integer=True),
    _f("population_type", "metadata", True, "enum", "—",
       "One of: " + ", ".join(POPULATION_TYPES) + ". Only "
       f"'{FULL_BOARD_POPULATION}' is eligible for the General Board."),
    _f("draft_size", "metadata", False, "integer", "picks",
       "Total picks in the draft this class enters. Required for the "
       "General Board; leave empty otherwise.",
       minimum=1, maximum=200, integer=True),
]

# --------------------------------------------------------------- prospects
IDENTITY_FIELDS = [
    _f("prospect_id", "identity", True, "string", "—",
       "Your own unique id for the player. Must be unique in the file."),
    _f("name", "identity", True, "string", "—", "Display name."),
    _f("school", "identity", False, "string", "—", "College or team name."),
    _f("position", "identity", True, "enum", "—",
       "One of G, F, C, UNKNOWN. Use UNKNOWN rather than guessing."),
]

PHYSICAL_FIELDS = [
    _f("height_inches", "physical", False, "number", "inches",
       "Height in inches (6'8\" = 80). Required for the Size dimension and "
       "for NBA Comparables, which gate candidates on plausible height.",
       minimum=48, maximum=96),
    _f("weight_lbs", "physical", False, "number", "pounds",
       "Playing weight in pounds.", minimum=100, maximum=400),
]

PLAYING_TIME_FIELDS = [
    _f("games_played", "box", True, "integer", "games",
       "Games played in the season.", minimum=0, maximum=80, integer=True),
    _f("games_started", "box", False, "integer", "games",
       "Games started. Feeds the starter-share model feature.",
       minimum=0, maximum=80, integer=True),
    _f("minutes", "box", True, "number", "minutes",
       "TOTAL minutes for the season, not minutes per game.",
       minimum=0, maximum=2000),
]

_BOX = [
    ("points", "Total points.", 3000),
    ("field_goals_made", "Total field goals made (all field goals).", 1200),
    ("field_goals_attempted", "Total field goals attempted.", 2500),
    ("three_points_made", "Total three-pointers made.", 500),
    ("three_points_attempted", "Total three-pointers attempted.", 1200),
    ("free_throws_made", "Total free throws made.", 800),
    ("free_throws_attempted", "Total free throws attempted.", 1000),
    ("offensive_rebounds", "Total offensive rebounds.", 600),
    ("defensive_rebounds", "Total defensive rebounds.", 900),
    ("total_rebounds", "Total rebounds (offensive + defensive).", 1500),
    ("assists", "Total assists.", 800),
    ("turnovers", "Total turnovers.", 500),
    ("steals", "Total steals.", 300),
    ("blocks", "Total blocks.", 300),
    ("personal_fouls", "Total personal fouls.", 200),
]
BOX_FIELDS = [_f(n, "box", True, "integer", "count", d, minimum=0,
                 maximum=mx, integer=True) for n, d, mx in _BOX]

_TEAM = [
    ("team_minutes", "Team minutes across the games this player appeared in."),
    ("team_field_goals_made", "Team field goals made in those games."),
    ("team_field_goals_attempted", "Team field goals attempted in those games."),
    ("team_free_throws_attempted", "Team free throws attempted in those games."),
    ("team_turnovers", "Team turnovers in those games."),
    ("team_offensive_rebounds", "Team offensive rebounds in those games."),
    ("team_defensive_rebounds", "Team defensive rebounds in those games."),
    ("team_rebounds", "Team total rebounds in those games."),
    ("opp_field_goals_attempted", "Opponent field goals attempted in those games."),
    ("opp_three_points_attempted", "Opponent three-pointers attempted."),
    ("opp_free_throws_attempted", "Opponent free throws attempted."),
    ("opp_offensive_rebounds", "Opponent offensive rebounds."),
    ("opp_defensive_rebounds", "Opponent defensive rebounds."),
    ("opp_rebounds", "Opponent total rebounds."),
    ("opp_turnovers", "Opponent turnovers."),
]
TEAM_CONTEXT_FIELDS = [
    _f(n, "team_context", False, "number", "count", d, minimum=0)
    for n, d in _TEAM]

_SHOT = [
    ("shot_records", "Total shot events recorded for this player. Team Need "
                     "reads this to decide whether rim finishing rests on "
                     "enough attempts to be reported at all."),
    ("shot_fg_attempts", "Field-goal attempts recorded in your shot data."),
    ("shot_fg_makes", "Field goals made recorded in your shot data."),
    ("layup_attempts", "Layup attempts."),
    ("layup_makes", "Layups made."),
    ("dunk_attempts", "Dunk attempts."),
    ("dunk_makes", "Dunks made."),
    ("tip_attempts", "Tip-in attempts."),
    ("tip_makes", "Tip-ins made."),
    ("assisted_made_field_goals", "Made field goals that were assisted."),
    ("unassisted_made_field_goals", "Made field goals that were unassisted."),
    ("assisted_layup_makes", "Made layups that were assisted."),
    ("unassisted_layup_makes", "Made layups that were unassisted."),
]
SHOT_PROFILE_FIELDS = [
    _f(n, "shot_profile", False, "number", "count", d, minimum=0)
    for n, d in _SHOT]

PROSPECT_FIELDS = (IDENTITY_FIELDS + PHYSICAL_FIELDS + PLAYING_TIME_FIELDS
                   + BOX_FIELDS + TEAM_CONTEXT_FIELDS + SHOT_PROFILE_FIELDS)

GROUPS = {
    "identity": "Who the player is.",
    "physical": "Measurements. Height unlocks Size and NBA Comparables.",
    "box": "Season box-score totals. Required.",
    "team_context": "Team and opponent totals over the player's games. "
                    "Unlocks usage, assist, rebound, steal and block rates.",
    "shot_profile": "Shot-location counts from play-by-play. Unlocks the "
                    "Rim Pressure dimension and the shot-profile model "
                    "features.",
}

# --------------------------------------------------------------- refusals
# A column stating what actually happened. Imported analysis is pre-draft, so
# any of these is an ERROR: the file is rejected rather than silently stripped.
PROHIBITED_FIELDS = [
    "drafted", "was_drafted", "undrafted", "pick", "actual_pick", "draft_pick",
    "pick_number", "draft_position", "draft_team", "team_drafted_by",
    "actual_round", "draft_round", "round", "draft_year_outcome",
    "nba_team", "nba_career", "career_ws", "career_vorp", "career_points",
    "outcome", "result", "selected",
]

# Rate-style columns a user might supply out of habit. They are refused with a
# specific explanation rather than a generic "unknown column", because the
# right fix (send the counts instead) is not obvious otherwise.
DERIVED_RATE_FIELDS = [
    "fg_pct", "field_goal_pct", "three_point_pct", "3p_pct", "ft_pct",
    "free_throw_pct", "efg_pct", "ts_pct", "usage_pct", "ast_pct", "tov_pct",
    "orb_pct", "drb_pct", "trb_pct", "stl_pct", "blk_pct",
    "points_per_game", "ppg", "rebounds_per_game", "rpg", "assists_per_game",
    "apg", "minutes_per_game", "mpg", "points_per_40",
]

# ------------------------------------------------------------------ limits
# A draft class, not a data warehouse. These bound what the browser will try
# to hold in memory and parse on the main thread.
EXCEL_METADATA_SHEET = "metadata"
EXCEL_PROSPECTS_SHEET = "prospects"

LIMITS = {
    "maxFileBytes": 8 * 1024 * 1024,
    "maxRows": 2000,
    "minRows": 5,
}


# ------------------------------------------------- schema for the frontend
def schema():
    """The complete machine-readable format, embedded in the runtime bundle."""
    return {
        "schemaVersion": SCHEMA_VERSION,
        "name": "DraftLens Dataset Format",
        "positions": list(POSITIONS),
        "populationTypes": dict(POPULATION_TYPES),
        "fullBoardPopulation": FULL_BOARD_POPULATION,
        "groups": dict(GROUPS),
        "metadataFields": [dict(f) for f in METADATA_FIELDS],
        "prospectFields": [dict(f) for f in PROSPECT_FIELDS],
        "prohibitedFields": list(PROHIBITED_FIELDS),
        "derivedRateFields": list(DERIVED_RATE_FIELDS),
        "limits": dict(LIMITS),
        "excelSheets": {"metadata": EXCEL_METADATA_SHEET,
                        "prospects": EXCEL_PROSPECTS_SHEET},
        "templates": {
            "json": "templates/draftlens_dataset_template.json",
            "excel": "templates/draftlens_dataset_template.xlsx",
        },
    }


def required_prospect_fields():
    return [f["name"] for f in PROSPECT_FIELDS if f["required"]]


def group_fields(group):
    return [f["name"] for f in PROSPECT_FIELDS if f["group"] == group]


# ------------------------------------------------------------- the mapping
# Import column -> the primitive name `features.basketball.build_features`
# reads. Only a rename: no arithmetic happens here, so the engineered layer a
# user's file reaches is byte-for-byte the one DraftLens's own data reaches.
TO_PRIMITIVE = {
    "team_minutes": "tm_minutes",
    "team_field_goals_made": "tm_field_goals_made",
    "team_field_goals_attempted": "tm_field_goals_attempted",
    "team_free_throws_attempted": "tm_free_throws_attempted",
    "team_turnovers": "tm_turnovers",
    "team_offensive_rebounds": "tm_offensive_rebounds",
    "team_defensive_rebounds": "tm_defensive_rebounds",
    "team_rebounds": "tm_rebounds",
    "opp_field_goals_attempted": "opp_field_goals_attempted",
    "opp_three_points_attempted": "opp_three_point_field_goals_attempted",
    "opp_free_throws_attempted": "opp_free_throws_attempted",
    "opp_offensive_rebounds": "opp_offensive_rebounds",
    "opp_defensive_rebounds": "opp_defensive_rebounds",
    "opp_rebounds": "opp_rebounds",
    "opp_turnovers": "opp_turnovers",
    "shot_fg_attempts": "fg_attempts_shotfile",
    "shot_fg_makes": "fg_makes_shotfile",
    "height_inches": "height",
    "weight_lbs": "weight",
}

# The reverse direction, used to write a DraftLens-format file out of an
# internal frame (the parity fixture and the worked template example).
FROM_PRIMITIVE = {v: k for k, v in TO_PRIMITIVE.items()}


# Columns `features.basketball.build_features` reads by attribute rather than
# through `.get`. An imported file that omits an optional group still has to
# present the column, holding NaN — which is exactly how the frozen pipeline
# expresses "not measured".
REQUIRED_PRIMITIVES = [
    "games_played", "games_started", "minutes",
    "points", "field_goals_made", "field_goals_attempted",
    "two_points_made", "two_points_attempted",
    "three_points_made", "three_points_attempted",
    "free_throws_made", "free_throws_attempted",
    "offensive_rebounds", "defensive_rebounds", "total_rebounds",
    "assists", "turnovers", "steals", "blocks", "personal_fouls",
    "shot_records", "fg_attempts_shotfile", "fg_makes_shotfile",
    "three_point_shot_attempts",
    "layup_attempts", "layup_makes", "dunk_attempts", "dunk_makes",
    "tip_attempts", "tip_makes",
    "assisted_made_field_goals", "unassisted_made_field_goals",
    "assisted_layup_makes", "unassisted_layup_makes",
    "assisted_dunk_makes", "unassisted_dunk_makes",
    "height", "weight",
]


def to_internal_frame(rows, season):
    """An imported prospect list -> the frame `build_features` expects.

    Renames only, plus the two identities `build_features` reads directly
    (`two_points_*` = all field goals minus threes). Every rate is computed
    downstream by the frozen code, so a user's file and DraftLens's own data
    reach the engineered layer through one implementation.
    """
    import numpy as np
    import pandas as pd

    df = pd.DataFrame(list(rows))
    df = df.rename(columns={k: v for k, v in TO_PRIMITIVE.items()
                            if k in df.columns})
    for c in ("field_goals_made", "three_points_made",
              "field_goals_attempted", "three_points_attempted"):
        if c not in df.columns:
            df[c] = np.nan
    df["two_points_made"] = df.field_goals_made - df.three_points_made
    df["two_points_attempted"] = (df.field_goals_attempted
                                  - df.three_points_attempted)
    for c in REQUIRED_PRIMITIVES:
        if c not in df.columns:
            df[c] = np.nan
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["draft_year"] = int(season)
    # The imported position goes through the SAME `to_position_3` mapping
    # DraftLens's own data does — `build_features` reads `hoopr_position` and
    # would otherwise mark every imported player UNKNOWN.
    df["hoopr_position"] = (df["position"] if "position" in df.columns
                            else "UNKNOWN")
    df["canonical_prospect_id"] = df.get("prospect_id")
    df["player_name"] = df.get("name")
    df["college"] = df.get("school")
    return df


# ---------------------------------------------------------------- template
EXAMPLE_ROW = {
    "prospect_id": "P001", "name": "Example Player", "school": "State",
    "position": "F", "height_inches": 80, "weight_lbs": 215,
    "games_played": 33, "games_started": 30, "minutes": 1050,
    "points": 520, "field_goals_made": 190, "field_goals_attempted": 400,
    "three_points_made": 55, "three_points_attempted": 150,
    "free_throws_made": 85, "free_throws_attempted": 110,
    "offensive_rebounds": 70, "defensive_rebounds": 180,
    "total_rebounds": 250, "assists": 95, "turnovers": 60, "steals": 40,
    "blocks": 25, "personal_fouls": 70,
}


def json_template():
    """A minimal, valid file a user can open and edit."""
    return {
        "schemaVersion": SCHEMA_VERSION,
        "metadata": {
            "dataset_name": "My Draft Class",
            "season": 2026,
            "population_type": FULL_BOARD_POPULATION,
            "draft_size": 60,
        },
        "prospects": [dict(EXAMPLE_ROW)],
    }


def metadata_rows():
    return [
        ["Key", "Value"],
        ["schema_version", SCHEMA_VERSION],
        ["dataset_name", "My Draft Class"],
        ["season", 2026],
        ["population_type", FULL_BOARD_POPULATION],
        ["draft_size", 60],
    ]


def prospect_rows():
    header = [f["name"] for f in PROSPECT_FIELDS]
    return [header, [EXAMPLE_ROW.get(name, None) for name in header]]


# ---------------------------------------------------- minimal xlsx writer
# An .xlsx is a zip of XML parts. Writing the handful this template needs
# takes the standard library alone, which keeps a spreadsheet-authoring
# dependency out of a project that only ever needs to emit ONE fixed file.
# `tests/integration/test_dataset_format.py` reads the result back to prove
# it is a workbook and not merely a well-formed zip.
def _column_name(index):
    name = ""
    while index >= 0:
        name = chr(ord("A") + index % 26) + name
        index = index // 26 - 1
    return name


def _escape(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def _sheet_xml(rows):
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           '<worksheet xmlns="http://schemas.openxmlformats.org/'
           'spreadsheetml/2006/main"><sheetData>']
    for r, row in enumerate(rows, start=1):
        out.append(f'<row r="{r}">')
        for c, value in enumerate(row):
            ref = f"{_column_name(c)}{r}"
            if value is None or value == "":
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                out.append(f'<c r="{ref}" t="inlineStr"><is><t>'
                           f'{_escape(value)}</t></is></c>')
            else:
                out.append(f'<c r="{ref}"><v>{value}</v></c>')
        out.append("</row>")
    out.append("</sheetData></worksheet>")
    return "".join(out)


def excel_template_bytes():
    """The two-sheet workbook a user downloads, as bytes."""
    import io
    import zipfile

    sheets = [(EXCEL_METADATA_SHEET, metadata_rows()),
              (EXCEL_PROSPECTS_SHEET, prospect_rows())]

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
        'content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats'
        '-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.'
        'openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + "".join(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
            f'ContentType="application/vnd.openxmlformats-officedocument.'
            f'spreadsheetml.worksheet+xml"/>'
            for i in range(1, len(sheets) + 1))
        + "</Types>")

    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
            '2006/relationships"><Relationship Id="rId1" Type="http://schemas.'
            'openxmlformats.org/officeDocument/2006/relationships/officeDocument"'
            ' Target="xl/workbook.xml"/></Relationships>')

    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/'
                'spreadsheetml/2006/main" xmlns:r="http://schemas.'
                'openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                + "".join(f'<sheet name="{name}" sheetId="{i}" '
                          f'r:id="rId{i}"/>'
                          for i, (name, _) in enumerate(sheets, start=1))
                + "</sheets></workbook>")

    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
        'relationships">'
        + "".join(f'<Relationship Id="rId{i}" Type="http://schemas.'
                  f'openxmlformats.org/officeDocument/2006/relationships/'
                  f'worksheet" Target="worksheets/sheet{i}.xml"/>'
                  for i in range(1, len(sheets) + 1))
        + "</Relationships>")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        for i, (_, rows) in enumerate(sheets, start=1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", _sheet_xml(rows))
    return buffer.getvalue()


TEMPLATE_DIR = None   # set by `write_templates`


def write_templates(directory=None, log=print):
    """Write both downloadable templates next to the app's static assets."""
    import json

    from paths import ROOT

    directory = directory or (ROOT / "app" / "public" / "templates")
    directory.mkdir(parents=True, exist_ok=True)

    json_path = directory / "draftlens_dataset_template.json"
    json_path.write_text(json.dumps(json_template(), indent=2))
    xlsx_path = directory / "draftlens_dataset_template.xlsx"
    xlsx_path.write_bytes(excel_template_bytes())

    log(f"  {json_path.name}  {json_path.stat().st_size / 1024:.1f} KB")
    log(f"  {xlsx_path.name}  {xlsx_path.stat().st_size / 1024:.1f} KB")
    return json_path, xlsx_path
