import { redirect } from "next/navigation";
import { createServerSupabase } from "@/lib/supabase-server";

export default async function RootPage() {
  const sb = await createServerSupabase();
  const {
    data: { user },
  } = await sb.auth.getUser();

  if (user) {
    redirect("/market");
  } else {
    redirect("/login");
  }
}
