"use client";

import { useEffect, useState } from "react";
import { getMarketIndices, type MarketIndex } from "@/lib/api";
import MarketMap from "@/components/MarketMap";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Grid";
import Chip from "@mui/material/Chip";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import TrendingFlatIcon from "@mui/icons-material/TrendingFlat";
import Skeleton from "@mui/material/Skeleton";

function TrendIcon({ trend }: { trend: string | null }) {
  if (trend === "up") return <TrendingUpIcon fontSize="small" color="error" />;
  if (trend === "down")
    return <TrendingDownIcon fontSize="small" color="success" />;
  return <TrendingFlatIcon fontSize="small" color="warning" />;
}

function trendChipColor(
  trend: string | null
): "error" | "success" | "warning" {
  if (trend === "up") return "error";
  if (trend === "down") return "success";
  return "warning";
}

export default function MarketPage() {
  const [indices, setIndices] = useState<MarketIndex[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMarketIndices()
      .then(setIndices)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const hottest = [...indices]
    .sort(
      (a, b) =>
        (b.load_to_truck_ratio ?? 0) - (a.load_to_truck_ratio ?? 0)
    )
    .slice(0, 5);

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Market Overview
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Real-time load density and rate trends across the US.
      </Typography>

      {/* Summary cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">
                Active Regions
              </Typography>
              <Typography variant="h4">
                {loading ? <Skeleton width={40} /> : indices.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">
                Hottest Market
              </Typography>
              <Typography variant="h5">
                {loading ? (
                  <Skeleton width={120} />
                ) : (
                  hottest[0]?.region || "—"
                )}
              </Typography>
              {hottest[0] && (
                <Typography variant="body2" color="text.secondary">
                  {hottest[0].load_to_truck_ratio} load/truck ratio
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">
                Avg Rate (Top 5)
              </Typography>
              <Typography variant="h4">
                {loading ? (
                  <Skeleton width={60} />
                ) : hottest.length ? (
                  `$${(
                    hottest.reduce(
                      (s, m) => s + (m.avg_rate_per_mile ?? 0),
                      0
                    ) / hottest.length
                  ).toFixed(2)}/mi`
                ) : (
                  "—"
                )}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Map */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 0, "&:last-child": { pb: 0 }, height: 480 }}>
          {loading ? (
            <Skeleton variant="rectangular" height={480} />
          ) : (
            <MarketMap indices={indices} />
          )}
        </CardContent>
      </Card>

      {/* Regional table */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Regional Breakdown
          </Typography>
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
                  <th style={{ padding: "10px 12px" }}>Region</th>
                  <th style={{ padding: "10px 12px" }}>Load/Truck</th>
                  <th style={{ padding: "10px 12px" }}>Avg Rate</th>
                  <th style={{ padding: "10px 12px" }}>Trend</th>
                  <th style={{ padding: "10px 12px" }}>Top Equipment</th>
                </tr>
              </thead>
              <tbody>
                {indices.map((idx) => (
                  <tr
                    key={idx.id}
                    style={{ borderBottom: "1px solid #f1f3f4" }}
                  >
                    <td style={{ padding: "10px 12px", fontWeight: 500 }}>
                      {idx.region}
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      {idx.load_to_truck_ratio}
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      ${idx.avg_rate_per_mile}/mi
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <Chip
                        icon={<TrendIcon trend={idx.trend} />}
                        label={idx.trend?.toUpperCase()}
                        size="small"
                        color={trendChipColor(idx.trend)}
                        variant="outlined"
                      />
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      {idx.equipment_type?.replace("_", " ")}
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
