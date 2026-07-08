"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const res = await fetch("/api/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, name }),
      credentials: "include"
    });
    if (res.ok) router.push("/login?registered=1");
    else setError((await res.text()) || "Signup failed");
  }

  return (
    <main className="flex min-h-dvh items-center justify-center px-6">
      <div className="surface mx-auto w-full max-w-md p-8">
        <h1 className="text-2xl font-semibold">Create account</h1>
        <p className="mt-2 text-sm text-muted-foreground">Start your Synzept workspace</p>
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <label className="block space-y-2 text-sm">
            <span>Name</span>
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label className="block space-y-2 text-sm">
            <span>Email</span>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label className="block space-y-2 text-sm">
            <span>Password</span>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
          </label>
          {error ? <p className="text-sm text-red-400">{error}</p> : null}
          <Button type="submit" variant="primary" className="w-full">
            Create account
          </Button>
        </form>
        <p className="mt-6 text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link href="/login" className="text-primary hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
