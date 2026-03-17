"use client";

import Chip from "@mui/material/Chip";
import StarIcon from "@mui/icons-material/Star";
import ThumbUpIcon from "@mui/icons-material/ThumbUp";
import RemoveIcon from "@mui/icons-material/Remove";

export default function ProfitabilityBadge({ score }: { score: number }) {
  if (score >= 70) {
    return (
      <Chip
        icon={<StarIcon />}
        label={`${score}% — Top Pick`}
        color="success"
        size="small"
      />
    );
  }
  if (score >= 45) {
    return (
      <Chip
        icon={<ThumbUpIcon />}
        label={`${score}% — Good Fit`}
        color="primary"
        size="small"
        variant="outlined"
      />
    );
  }
  return (
    <Chip
      icon={<RemoveIcon />}
      label={`${score}% — Below Avg`}
      size="small"
      variant="outlined"
    />
  );
}
