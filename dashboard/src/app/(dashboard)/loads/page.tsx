"use client";

import { useEffect, useState } from "react";
import { getRecommendedLoads, type ScoredLoad } from "@/lib/api";
import ProfitabilityBadge from "@/components/ProfitabilityBadge";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import IconButton from "@mui/material/IconButton";
import Skeleton from "@mui/material/Skeleton";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import Stack from "@mui/material/Stack";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import LocalShippingIcon from "@mui/icons-material/LocalShipping";

const EQUIP_LABELS: Record<string, string> = {
  dry_van: "Dry Van",
  reefer: "Reefer",
  flatbed: "Flatbed",
  step_deck: "Step Deck",
  tanker: "Tanker",
};

export default function LoadsPage() {
  const [loads, setLoads] = useState<ScoredLoad[]>([]);
  const [loading, setLoading] = useState(true);
  const [equipFilter, setEquipFilter] = useState("all");
  const [sortBy, setSortBy] = useState<"fit_score" | "rate_per_mile" | "miles">(
    "fit_score"
  );

  useEffect(() => {
    getRecommendedLoads(50)
      .then(setLoads)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = loads
    .filter((l) => equipFilter === "all" || l.equipment_type === equipFilter)
    .sort((a, b) => {
      if (sortBy === "fit_score") return b.fit_score - a.fit_score;
      if (sortBy === "rate_per_mile")
        return (b.rate_per_mile ?? 0) - (a.rate_per_mile ?? 0);
      return (b.miles ?? 0) - (a.miles ?? 0);
    });

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Recommended Loads
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Loads ranked by AI-powered fit score based on your profile, lanes, and
        market conditions.
      </Typography>

      {/* Filters */}
      <Stack direction="row" gap={2} sx={{ mb: 3 }} flexWrap="wrap">
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>Equipment</InputLabel>
          <Select
            value={equipFilter}
            label="Equipment"
            onChange={(e) => setEquipFilter(e.target.value)}
          >
            <MenuItem value="all">All Types</MenuItem>
            {Object.entries(EQUIP_LABELS).map(([val, label]) => (
              <MenuItem key={val} value={val}>
                {label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>Sort By</InputLabel>
          <Select
            value={sortBy}
            label="Sort By"
            onChange={(e) =>
              setSortBy(e.target.value as "fit_score" | "rate_per_mile" | "miles")
            }
          >
            <MenuItem value="fit_score">Fit Score</MenuItem>
            <MenuItem value="rate_per_mile">Rate/Mile</MenuItem>
            <MenuItem value="miles">Distance</MenuItem>
          </Select>
        </FormControl>

        <Chip
          icon={<LocalShippingIcon />}
          label={`${filtered.length} loads`}
          variant="outlined"
        />
      </Stack>

      {/* Table */}
      <Card>
        <CardContent sx={{ p: 0 }}>
          <Box sx={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: 14,
              }}
            >
              <thead>
                <tr
                  style={{
                    borderBottom: "2px solid #e8eaed",
                    textAlign: "left",
                  }}
                >
                  <th style={{ padding: "12px 16px" }}>Match</th>
                  <th style={{ padding: "12px 16px" }}>Origin</th>
                  <th style={{ padding: "12px 16px" }}>Destination</th>
                  <th style={{ padding: "12px 16px" }}>Equipment</th>
                  <th style={{ padding: "12px 16px" }}>Miles</th>
                  <th style={{ padding: "12px 16px" }}>Rate/mi</th>
                  <th style={{ padding: "12px 16px" }}>Total</th>
                  <th style={{ padding: "12px 16px" }}>Pickup</th>
                  <th style={{ padding: "12px 16px" }}>Broker</th>
                  <th style={{ padding: "12px 16px" }}>Insight</th>
                </tr>
              </thead>
              <tbody>
                {loading
                  ? Array.from({ length: 8 }).map((_, i) => (
                      <tr key={i}>
                        {Array.from({ length: 10 }).map((_, j) => (
                          <td key={j} style={{ padding: "12px 16px" }}>
                            <Skeleton />
                          </td>
                        ))}
                      </tr>
                    ))
                  : filtered.map((load) => (
                      <tr
                        key={load.id}
                        style={{ borderBottom: "1px solid #f1f3f4" }}
                      >
                        <td style={{ padding: "12px 16px" }}>
                          <ProfitabilityBadge score={load.fit_score} />
                        </td>
                        <td style={{ padding: "12px 16px", fontWeight: 500 }}>
                          {load.origin_city}, {load.origin_state}
                        </td>
                        <td style={{ padding: "12px 16px" }}>
                          {load.dest_city}, {load.dest_state}
                        </td>
                        <td style={{ padding: "12px 16px" }}>
                          <Chip
                            label={
                              EQUIP_LABELS[load.equipment_type] ||
                              load.equipment_type
                            }
                            size="small"
                            variant="outlined"
                          />
                        </td>
                        <td style={{ padding: "12px 16px" }}>
                          {load.miles?.toLocaleString()}
                        </td>
                        <td
                          style={{
                            padding: "12px 16px",
                            fontWeight: 600,
                            color: "#1a73e8",
                          }}
                        >
                          ${load.rate_per_mile}
                        </td>
                        <td style={{ padding: "12px 16px" }}>
                          ${load.total_rate?.toLocaleString()}
                        </td>
                        <td style={{ padding: "12px 16px" }}>
                          {load.pickup_date}
                        </td>
                        <td style={{ padding: "12px 16px", fontSize: 13 }}>
                          {load.broker_name}
                        </td>
                        <td style={{ padding: "12px 16px" }}>
                          {load.market_summary ? (
                            <Tooltip title={load.market_summary} arrow>
                              <IconButton size="small" color="primary">
                                <InfoOutlinedIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          ) : (
                            "—"
                          )}
                        </td>
                      </tr>
                    ))}
              </tbody>
            </table>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
