import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({ message: "Auth endpoint - Supabase handles auth" });
}
