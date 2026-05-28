"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Image from "next/image";
import { Aperture } from "lucide-react";
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
    <div className="relative min-h-screen flex items-center justify-center p-6">

      {/* Background — real MRI suite photograph from Unsplash */}
      <Image
        src="https://images.unsplash.com/photo-1530026405186-ed1f139313f8?w=1920&auto=format&fit=crop&q=60"
        alt=""
        fill
        className="object-cover object-center"
        priority
      />

      {/* Light green wash so the form stays readable */}
      <div
        className="absolute inset-0"
        style={{ backgroundColor: "rgba(220, 242, 224, 0.87)" }}
      />

      <div className="relative z-10 w-full max-w-md">

        {/* Logo */}
        <div className="flex items-center gap-4 mb-10">
          <div
            className="w-14 h-14 rounded-2xl flex items-center justify-center shadow-md"
            style={{ backgroundColor: "#2E7D32" }}
          >
            <Aperture size={30} className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: "#1A1A1A" }}>RadSight</h1>
            <p className="text-sm font-medium mt-0.5" style={{ color: "#4A6741" }}>
              Radiology Command Centre
            </p>
          </div>
        </div>

        {/* Card */}
        <div
          className="rounded-2xl p-9 shadow-lg"
          style={{
            backgroundColor: "#FFFFFF",
            border: "1px solid #C8E6C9",
          }}
        >
          <h2 className="text-xl font-semibold mb-1.5" style={{ color: "#111111" }}>
            Sign in to your workspace
          </h2>
          <p className="text-base mb-8" style={{ color: "#555555" }}>
            Enter your credentials to access RadSight
          </p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div className="flex flex-col gap-2">
              <label className="text-base font-medium" style={{ color: "#222222" }}>
                Email address
              </label>
              <input
                type="email"
                placeholder="you@hospital.org"
                autoComplete="email"
                {...register("email")}
                className="w-full rounded-lg px-4 py-3 text-base outline-none transition-colors"
                style={{
                  backgroundColor: "#F7FBF7",
                  border: "1px solid #A5D6A7",
                  color: "#111111",
                }}
                onFocus={(e) => (e.target.style.borderColor = "#2E7D32")}
                onBlur={(e) => (e.target.style.borderColor = "#A5D6A7")}
              />
              {errors.email && (
                <p className="text-sm" style={{ color: "#C62828" }}>{errors.email.message}</p>
              )}
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-base font-medium" style={{ color: "#222222" }}>
                Password
              </label>
              <input
                type="password"
                placeholder="••••••••"
                autoComplete="current-password"
                {...register("password")}
                className="w-full rounded-lg px-4 py-3 text-base outline-none transition-colors"
                style={{
                  backgroundColor: "#F7FBF7",
                  border: "1px solid #A5D6A7",
                  color: "#111111",
                }}
                onFocus={(e) => (e.target.style.borderColor = "#2E7D32")}
                onBlur={(e) => (e.target.style.borderColor = "#A5D6A7")}
              />
              {errors.password && (
                <p className="text-sm" style={{ color: "#C62828" }}>{errors.password.message}</p>
              )}
            </div>

            {error && (
              <p className="text-base text-center" style={{ color: "#C62828" }}>{error}</p>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 rounded-lg text-base font-semibold text-white transition-opacity disabled:opacity-60"
              style={{ backgroundColor: "#2E7D32" }}
            >
              {isSubmitting ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <div className="mt-7 pt-6" style={{ borderTop: "1px solid #E8F5E9" }}>
            <p className="text-sm font-medium mb-2.5" style={{ color: "#777777" }}>
              Demo credentials
            </p>
            <div className="space-y-1.5 font-mono text-sm" style={{ color: "#555555" }}>
              <p>admin@radsight.health / RadSight@Admin2024</p>
              <p>radiologist@radsight.health / RadSight@Rad2024</p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
