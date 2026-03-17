"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import GoogleIcon from "@mui/icons-material/Google";

export default function LoginPage() {
  const [loading, setLoading] = useState(false);

  async function handleGoogleLogin() {
    setLoading(true);
    const sb = createClient();
    await sb.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/callback`,
      },
    });
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "background.default",
      }}
    >
      <Card sx={{ maxWidth: 420, width: "100%", mx: 2 }}>
        <CardContent
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 3,
            py: 6,
            px: 4,
          }}
        >
          <Typography variant="h4" fontWeight={700} color="primary">
            Noctem
          </Typography>
          <Typography variant="body1" color="text.secondary" textAlign="center">
            AI-powered freight dispatch.
            <br />
            Sign in to get started.
          </Typography>

          <Button
            variant="outlined"
            size="large"
            startIcon={
              loading ? <CircularProgress size={20} /> : <GoogleIcon />
            }
            onClick={handleGoogleLogin}
            disabled={loading}
            sx={{
              mt: 2,
              px: 4,
              py: 1.5,
              borderColor: "#dadce0",
              color: "text.primary",
              "&:hover": { borderColor: "#1a73e8", bgcolor: "#f0f4ff" },
            }}
          >
            Continue with Google
          </Button>
        </CardContent>
      </Card>
    </Box>
  );
}
