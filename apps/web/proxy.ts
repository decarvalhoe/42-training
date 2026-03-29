import { NextResponse, type NextRequest } from "next/server";

import { ACCESS_TOKEN_COOKIE_KEY } from "@/services/auth";

function normalizeNextPath(pathname: string, search: string) {
  return `${pathname}${search}`;
}

function isSafeRelativePath(value: string | null): value is string {
  return Boolean(value && value.startsWith("/") && !value.startsWith("//"));
}

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const token = request.cookies.get(ACCESS_TOKEN_COOKIE_KEY)?.value;

  if (pathname === "/login") {
    if (!token) {
      return NextResponse.next();
    }

    const requestedTarget = request.nextUrl.searchParams.get("next");
    const safeTarget = isSafeRelativePath(requestedTarget) ? requestedTarget : "/";
    return NextResponse.redirect(new URL(safeTarget, request.url));
  }

  if (token) {
    return NextResponse.next();
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.search = "";
  loginUrl.searchParams.set("next", normalizeNextPath(pathname, search));
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
