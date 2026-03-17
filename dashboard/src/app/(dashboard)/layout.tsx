import { redirect } from "next/navigation";
import { createServerSupabase } from "@/lib/supabase-server";
import Box from "@mui/material/Box";
import Sidebar from "@/components/Sidebar";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const sb = await createServerSupabase();
  const {
    data: { user },
  } = await sb.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          bgcolor: "background.default",
          p: 4,
          overflow: "auto",
        }}
      >
        {children}
      </Box>
    </Box>
  );
}
