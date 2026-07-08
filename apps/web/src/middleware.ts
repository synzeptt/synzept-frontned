import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC = ["/", "/login", "/signup"];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (!pathname.startsWith("/app")) {
    return NextResponse.next();
  }

  const sessionToken =
    req.cookies.get("next-auth.session-token")?.value ??
    req.cookies.get("__Secure-next-auth.session-token")?.value;

  if (!sessionToken && !PUBLIC.includes(pathname)) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("redirect", pathname);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/app/:path*"]
};
