"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createVoicePin,
  getTranscripts,
  type CallTranscript,
  type VoicePin,
} from "@/lib/api";
import { useRealtimeTable } from "@/lib/use-realtime";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Button from "@mui/material/Button";
import Alert from "@mui/material/Alert";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import PhoneInTalkIcon from "@mui/icons-material/PhoneInTalk";
import TranslateIcon from "@mui/icons-material/Translate";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import Skeleton from "@mui/material/Skeleton";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";

function formatDuration(seconds: number | null): string {
  if (!seconds) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function langLabel(lang: string | null): string {
  const map: Record<string, string> = {
    en: "English",
    es: "Spanish",
    pa: "Punjabi",
    english: "English",
    spanish: "Spanish",
    punjabi: "Punjabi",
  };
  return map[(lang || "").toLowerCase()] || lang || "Unknown";
}

export default function VoicePage() {
  const [transcripts, setTranscripts] = useState<CallTranscript[]>([]);
  const [loading, setLoading] = useState(true);
  const [pinInfo, setPinInfo] = useState<VoicePin | null>(null);
  const [pinLoading, setPinLoading] = useState(false);
  const [pinError, setPinError] = useState("");

  const refresh = useCallback(() => {
    getTranscripts(30)
      .then(setTranscripts)
      .catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    setLoading(false);
  }, [refresh]);

  // Auto-refresh when new transcripts arrive
  useRealtimeTable("call_transcripts", undefined, refresh);

  const pinExpiresLabel = useMemo(() => {
    if (!pinInfo?.expires_at) return "";
    const dt = new Date(pinInfo.expires_at);
    return dt.toLocaleTimeString();
  }, [pinInfo?.expires_at]);

  async function handleGeneratePin() {
    setPinError("");
    setPinLoading(true);
    try {
      const pin = await createVoicePin();
      setPinInfo(pin);
    } catch (e: unknown) {
      setPinError(e instanceof Error ? e.message : "Failed to create PIN");
    } finally {
      setPinLoading(false);
    }
  }

  async function handleCopyPin() {
    if (!pinInfo?.pin) return;
    await navigator.clipboard.writeText(pinInfo.pin);
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Voice Agent
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Recent call transcripts and AI summaries from the phone dispatcher.
      </Typography>

      {/* Status card */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" alignItems="center" gap={2}>
            <PhoneInTalkIcon color="primary" sx={{ fontSize: 40 }} />
            <Box>
              <Typography variant="h6">Noctem Dispatch Line</Typography>
              <Typography variant="body2" color="text.secondary">
                Call your Twilio number to speak with the AI dispatcher.
                Supports English, Spanish, and Punjabi.
              </Typography>
            </Box>
            <Box sx={{ flexGrow: 1 }} />
            <Chip
              label={`${transcripts.length} calls`}
              variant="outlined"
              color="primary"
            />
          </Stack>

          <Box sx={{ mt: 3 }}>
            <Typography variant="subtitle2" gutterBottom>
              Link your call with a PIN
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              Generate a 6-digit PIN, then call the dispatch number and say: “My PIN is ######”.
              This links the phone call to your carrier profile so the agent can find your best loads and update your lanes.
            </Typography>

            {pinError && (
              <Alert severity="error" sx={{ mb: 1.5 }} onClose={() => setPinError("")}>
                {pinError}
              </Alert>
            )}

            <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap">
              <Button
                variant="contained"
                onClick={handleGeneratePin}
                disabled={pinLoading}
              >
                {pinLoading ? "Generating..." : pinInfo ? "Generate new PIN" : "Generate PIN"}
              </Button>

              {pinInfo && (
                <>
                  <Chip
                    label={`PIN: ${pinInfo.pin}`}
                    color="secondary"
                    variant="outlined"
                    sx={{ fontWeight: 700, letterSpacing: 1 }}
                  />
                  <Button
                    size="small"
                    startIcon={<ContentCopyIcon fontSize="small" />}
                    onClick={handleCopyPin}
                  >
                    Copy
                  </Button>
                  <Chip
                    size="small"
                    label={`Expires: ${pinExpiresLabel}`}
                    variant="outlined"
                  />
                </>
              )}
            </Stack>
          </Box>
        </CardContent>
      </Card>

      {/* Transcripts */}
      {loading ? (
        Array.from({ length: 3 }).map((_, i) => (
          <Skeleton
            key={i}
            variant="rectangular"
            height={72}
            sx={{ borderRadius: 2, mb: 1 }}
          />
        ))
      ) : transcripts.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: "center", py: 6 }}>
            <PhoneInTalkIcon
              sx={{ fontSize: 64, color: "text.disabled", mb: 2 }}
            />
            <Typography variant="h6" color="text.secondary">
              No calls yet
            </Typography>
            <Typography variant="body2" color="text.disabled">
              Call your Twilio number to start. Transcripts will appear here
              automatically.
            </Typography>
          </CardContent>
        </Card>
      ) : (
        transcripts.map((t) => (
          <Accordion
            key={t.id}
            sx={{
              mb: 1,
              borderRadius: "12px !important",
              "&:before": { display: "none" },
              boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
            }}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Stack
                direction="row"
                alignItems="center"
                gap={2}
                sx={{ width: "100%" }}
              >
                <PhoneInTalkIcon color="action" />
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle2">
                    {new Date(t.created_at).toLocaleString()}
                  </Typography>
                  {t.ai_summary && (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      noWrap
                      sx={{ maxWidth: 500 }}
                    >
                      {t.ai_summary}
                    </Typography>
                  )}
                </Box>
                <Stack direction="row" gap={1}>
                  <Chip
                    icon={<TranslateIcon />}
                    label={langLabel(t.language_detected)}
                    size="small"
                    variant="outlined"
                  />
                  <Chip
                    icon={<AccessTimeIcon />}
                    label={formatDuration(t.duration_seconds)}
                    size="small"
                    variant="outlined"
                  />
                </Stack>
              </Stack>
            </AccordionSummary>
            <AccordionDetails>
              <Box sx={{ maxHeight: 300, overflowY: "auto" }}>
                {(t.transcript || []).map((entry, i) => (
                  <Box
                    key={i}
                    sx={{
                      display: "flex",
                      gap: 1,
                      mb: 1.5,
                      alignItems: "flex-start",
                    }}
                  >
                    <Chip
                      label={entry.role === "assistant" ? "AI" : "Caller"}
                      size="small"
                      color={
                        entry.role === "assistant" ? "primary" : "default"
                      }
                      sx={{ minWidth: 60 }}
                    />
                    <Typography variant="body2" sx={{ pt: 0.25 }}>
                      {entry.content}
                    </Typography>
                  </Box>
                ))}
              </Box>

              {t.actions_taken && t.actions_taken.length > 0 && (
                <Box sx={{ mt: 2, pt: 2, borderTop: "1px solid #e8eaed" }}>
                  <Typography
                    variant="overline"
                    color="text.secondary"
                    gutterBottom
                  >
                    Actions Taken
                  </Typography>
                  <Stack direction="row" gap={1} flexWrap="wrap">
                    {t.actions_taken.map((action, i) => (
                      <Chip
                        key={i}
                        label={
                          (action as Record<string, string>).type ||
                          JSON.stringify(action)
                        }
                        size="small"
                        color="secondary"
                        variant="outlined"
                      />
                    ))}
                  </Stack>
                </Box>
              )}
            </AccordionDetails>
          </Accordion>
        ))
      )}
    </Box>
  );
}
