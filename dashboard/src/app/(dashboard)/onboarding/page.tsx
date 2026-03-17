"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  onboardCarrier,
  getMyProfile,
  updateMyProfile,
  type CarrierProfile,
} from "@/lib/api";
import { useRealtimeTable } from "@/lib/use-realtime";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import Stepper from "@mui/material/Stepper";
import Step from "@mui/material/Step";
import StepLabel from "@mui/material/StepLabel";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";

const STEPS = ["Enter MC Number", "Confirm & Select Equipment", "Set Preferred Lanes"];

const EQUIPMENT_OPTIONS = [
  { value: "dry_van", label: "Dry Van" },
  { value: "reefer", label: "Reefer" },
  { value: "flatbed", label: "Flatbed" },
  { value: "step_deck", label: "Step Deck" },
  { value: "tanker", label: "Tanker" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [mc, setMc] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [profile, setProfile] = useState<CarrierProfile | null>(null);
  const [selectedEquipment, setSelectedEquipment] = useState<string[]>([]);
  const [lanes, setLanes] = useState<{ origin: string; destination: string }[]>([
    { origin: "", destination: "" },
  ]);

  const refreshProfile = useCallback(() => {
    getMyProfile()
      .then((p) => {
        setProfile(p);
        setSelectedEquipment(p.equipment_types || []);
        setLanes(
          p.preferred_lanes?.length
            ? p.preferred_lanes
            : [{ origin: "", destination: "" }]
        );
        if (step === 0) setStep(p.equipment_types?.length ? 2 : 1);
      })
      .catch(() => {});
  }, [step]);

  useEffect(() => { refreshProfile(); }, []);

  // Live-update when voice agent modifies the profile
  useRealtimeTable("carrier_profiles", undefined, refreshProfile);

  async function handleLookup() {
    setError("");
    setLoading(true);
    try {
      const p = await onboardCarrier(mc);
      setProfile(p);
      setStep(1);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Lookup failed");
    } finally {
      setLoading(false);
    }
  }

  function toggleEquipment(val: string) {
    setSelectedEquipment((prev) =>
      prev.includes(val) ? prev.filter((v) => v !== val) : [...prev, val]
    );
  }

  async function handleSaveEquipment() {
    setLoading(true);
    try {
      const p = await updateMyProfile({ equipment_types: selectedEquipment });
      setProfile(p);
      setStep(2);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveLanes() {
    setLoading(true);
    const valid = lanes.filter((l) => l.origin && l.destination);
    try {
      await updateMyProfile({ preferred_lanes: valid });
      router.push("/market");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box
      sx={{
        maxWidth: 640,
        mx: "auto",
        mt: 4,
      }}
    >
      <Typography variant="h4" gutterBottom>
        Get Started
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Set up your carrier profile in a few steps.
      </Typography>

      <Stepper activeStep={step} alternativeLabel sx={{ mb: 4 }}>
        {STEPS.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {/* Step 0: MC Number Input */}
      {step === 0 && (
        <Card>
          <CardContent sx={{ p: 4, display: "flex", flexDirection: "column", gap: 3 }}>
            <Typography variant="h6">What&apos;s your MC Number?</Typography>
            <TextField
              label="MC Number"
              placeholder="e.g. 1015298"
              value={mc}
              onChange={(e) => setMc(e.target.value)}
              fullWidth
              autoFocus
              onKeyDown={(e) => e.key === "Enter" && handleLookup()}
            />
            <Button
              variant="contained"
              size="large"
              onClick={handleLookup}
              disabled={!mc.trim() || loading}
              startIcon={loading ? <CircularProgress size={20} /> : undefined}
            >
              {loading ? "Looking up..." : "Look Up Carrier"}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Step 1: Confirm info + select equipment */}
      {step === 1 && profile && (
        <Card>
          <CardContent sx={{ p: 4, display: "flex", flexDirection: "column", gap: 3 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <CheckCircleIcon color="success" />
              <Typography variant="h6">
                {profile.legal_name || profile.dba_name}
              </Typography>
            </Box>
            <Typography variant="body2" color="text.secondary">
              MC {profile.mc_number} &middot; DOT {profile.dot_number} &middot;{" "}
              {profile.home_city}, {profile.home_state}
            </Typography>
            <Typography
              variant="body2"
              color={profile.allowed_to_operate ? "success.main" : "error.main"}
            >
              {profile.allowed_to_operate
                ? "Authorized to operate"
                : "NOT authorized to operate"}
            </Typography>

            <Typography variant="subtitle1" sx={{ mt: 2 }}>
              Select your equipment types:
            </Typography>
            <Stack direction="row" flexWrap="wrap" gap={1}>
              {EQUIPMENT_OPTIONS.map((eq) => (
                <Chip
                  key={eq.value}
                  label={eq.label}
                  clickable
                  color={
                    selectedEquipment.includes(eq.value) ? "primary" : "default"
                  }
                  variant={
                    selectedEquipment.includes(eq.value) ? "filled" : "outlined"
                  }
                  onClick={() => toggleEquipment(eq.value)}
                />
              ))}
            </Stack>

            <Button
              variant="contained"
              size="large"
              onClick={handleSaveEquipment}
              disabled={selectedEquipment.length === 0 || loading}
            >
              Continue
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Preferred Lanes */}
      {step === 2 && (
        <Card>
          <CardContent sx={{ p: 4, display: "flex", flexDirection: "column", gap: 3 }}>
            <Typography variant="h6">Preferred Lanes</Typography>
            <Typography variant="body2" color="text.secondary">
              Add origin-destination pairs to help us find the best loads for
              you.
            </Typography>

            {lanes.map((lane, i) => (
              <Stack key={i} direction="row" gap={1} alignItems="center">
                <TextField
                  label="Origin"
                  placeholder="e.g. Fresno, CA"
                  size="small"
                  value={lane.origin}
                  onChange={(e) => {
                    const next = [...lanes];
                    next[i] = { ...next[i], origin: e.target.value };
                    setLanes(next);
                  }}
                  sx={{ flex: 1 }}
                />
                <Typography color="text.secondary">&rarr;</Typography>
                <TextField
                  label="Destination"
                  placeholder="e.g. Chicago, IL"
                  size="small"
                  value={lane.destination}
                  onChange={(e) => {
                    const next = [...lanes];
                    next[i] = { ...next[i], destination: e.target.value };
                    setLanes(next);
                  }}
                  sx={{ flex: 1 }}
                />
                {lanes.length > 1 && (
                  <IconButton
                    size="small"
                    onClick={() => setLanes(lanes.filter((_, j) => j !== i))}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                )}
              </Stack>
            ))}

            <Button
              size="small"
              startIcon={<AddIcon />}
              onClick={() =>
                setLanes([...lanes, { origin: "", destination: "" }])
              }
            >
              Add another lane
            </Button>

            <Stack direction="row" gap={2}>
              <Button
                variant="outlined"
                onClick={() => router.push("/market")}
              >
                Skip for now
              </Button>
              <Button
                variant="contained"
                size="large"
                onClick={handleSaveLanes}
                disabled={loading}
              >
                Save & Continue
              </Button>
            </Stack>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
