"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { signIn } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect") ?? "/app";

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const res = await signIn("credentials", { email, password, redirect: false });
    if (res?.ok) router.push(redirect);
    else setError("Invalid email or password");
  }

  return (
    <div className="surface mx-auto w-full max-w-md p-8">
      <h1 className="text-2xl font-semibold">Sign in</h1>
      <p className="mt-2 text-sm text-muted-foreground">Access your Synzept workspace</p>
      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        <label className="block space-y-2 text-sm">
          <span>Email</span>
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
        </label>
        <label className="block space-y-2 text-sm">
          <span>Password</span>
          <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
        </label>
        {error ? <p className="text-sm text-red-400">{error}</p> : null}
        <Button type="submit" variant="primary" className="w-full">
          Sign in
        </Button>
      </form>
      <p className="mt-6 text-sm text-muted-foreground">
        No account?{" "}
        <Link href="/signup" className="text-primary hover:underline">
          Create one
        </Link>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <main className="flex min-h-dvh items-center justify-center px-6">
      <Suspense fallback={<div className="text-muted-foreground">Loading...</div>}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
