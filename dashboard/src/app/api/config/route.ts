import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    backendUrl: process.env.NEXT_PUBLIC_BACKEND_URL || "",
  });
}

