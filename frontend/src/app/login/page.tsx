"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Stethoscope } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useAuthStore } from "@/store/auth";
import { login } from "@/lib/auth";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

type LoginForm = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const { setUser } = useAuthStore();
  const [error, setError] = useState("");

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: LoginForm) => {
    setError("");
    try {
      const user = await login(data.email, data.password);
      setUser(user);
      router.push("/dashboard");
    } catch {
      setError("Invalid email or password");
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-6"
      style={{ backgroundColor: "#E6F4EA" }}
    >
      <div className="w-full max-w-md">

        {/* Logo */}
        <div className="flex items-center gap-3 mb-8">
          <div
            className="w-11 h-11 rounded-xl flex items-center justify-center shadow-md"
            style={{ backgroundColor: "#2E7D32" }}
          >
            <Stethoscope size={22} className="text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold" style={{ color: "#1A1A1A" }}>RadSight</h1>
            <p className="text-xs font-medium" style={{ color: "#4A6741" }}>
              Radiology Command Centre
            </p>
          </div>
        </div>

        {/* Card */}
        <div
          className="rounded-2xl p-8 shadow-lg"
          style={{
            backgroundColor: "#FFFFFF",
            border: "1px solid #C8E6C9",
          }}
        >
          <h2 className="text-base font-semibold mb-1" style={{ color: "#111111" }}>
            Sign in to your workspace
          </h2>
          <p className="text-sm mb-7" style={{ color: "#555555" }}>
            Enter your credentials to access RadSight
          </p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium" style={{ color: "#222222" }}>
                Email address
              </label>
              <input
                type="email"
                placeholder="you@hospital.org"
                autoComplete="email"
                {...register("email")}
                className="w-full rounded-lg px-3 py-2.5 text-sm outline-none transition-colors"
                style={{
                  backgroundColor: "#F7FBF7",
                  border: "1px solid #A5D6A7",
                  color: "#111111",
                }}
                onFocus={(e) => (e.target.style.borderColor = "#2E7D32")}
                onBlur={(e) => (e.target.style.borderColor = "#A5D6A7")}
              />
              {errors.email && (
                <p className="text-xs" style={{ color: "#C62828" }}>{errors.email.message}</p>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium" style={{ color: "#222222" }}>
                Password
              </label>
              <input
                type="password"
                placeholder="••••••••"
                autoComplete="current-password"
                {...register("password")}
                className="w-full rounded-lg px-3 py-2.5 text-sm outline-none transition-colors"
                style={{
                  backgroundColor: "#F7FBF7",
                  border: "1px solid #A5D6A7",
                  color: "#111111",
                }}
                onFocus={(e) => (e.target.style.borderColor = "#2E7D32")}
                onBlur={(e) => (e.target.style.borderColor = "#A5D6A7")}
              />
              {errors.password && (
                <p className="text-xs" style={{ color: "#C62828" }}>{errors.password.message}</p>
              )}
            </div>

            {error && (
              <p className="text-sm text-center" style={{ color: "#C62828" }}>{error}</p>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 rounded-lg text-sm font-semibold text-white transition-opacity disabled:opacity-60"
              style={{ backgroundColor: "#2E7D32" }}
            >
              {isSubmitting ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <div className="mt-6 pt-5" style={{ borderTop: "1px solid #E8F5E9" }}>
            <p className="text-xs font-medium mb-2" style={{ color: "#777777" }}>
              Demo credentials
            </p>
            <div className="space-y-1 font-mono text-xs" style={{ color: "#555555" }}>
              <p>admin@radsight.health / RadSight@Admin2024</p>
              <p>radiologist@radsight.health / RadSight@Rad2024</p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
