import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_ALB_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function POST(req: NextRequest) {
  try {
    // Forward multipart/form-data as-is to backend
    const formData = await req.formData();
    const res = await fetch(`${BACKEND_URL}/api/v1/voice/query`, {
      method: 'POST',
      body: formData,
      // Don't set Content-Type — fetch sets it automatically with boundary for multipart
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error('[proxy/voice/query] error:', err);
    return NextResponse.json({ error: 'Backend unreachable' }, { status: 502 });
  }
}
