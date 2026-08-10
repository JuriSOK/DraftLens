/** Contextual-help copy for the product's five headline scores.
 *
 * Centralised so the same concept reads identically everywhere it appears,
 * and so this short copy stays short — the full explanation of each lives on
 * the Methodology page, which every entry links to. None of these strings
 * describes a score as a probability of NBA success or a career projection. */
export const TOOLTIPS = {
  draftProbability: {
    text:
      "Estimated probability that this prospect is drafted, based on his pre-draft NCAA statistical profile and DraftLens's historical model. It is not a probability of NBA success.",
    href: "/methodology#draft-probability",
  },
  overallScore: {
    text:
      "Class-relative DraftLens ranking score from 0-100. It shows where the prospect's General Board signal sits within this prospect pool. It is not a probability.",
    href: "/methodology#overall-score",
  },
  basketballProfile: {
    text:
      "These 0-100 scores show how the prospect compares with NCAA reference players for each basketball trait.",
    href: "/methodology#team-need",
  },
  teamNeedFit: {
    text:
      "Shows how strongly the prospect's NCAA statistical profile matches the selected basketball need. For predefined archetypes, a higher score means the prospect fits that profile better relative to NCAA peers.",
    href: "/methodology#team-need",
  },
  comparables: {
    text:
      "NBA players with a plausible height and the closest statistical profiles in DraftLens's normalized comparison space. These are similarities, not career projections.",
    href: "/methodology#comparables",
  },
} as const;
