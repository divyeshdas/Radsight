"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import Image from "next/image";
import {
  LayoutDashboard, FileText, Search, BarChart3,
  LogOut, ChevronRight, FileScan,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { logout } from "@/lib/auth";
import { useRouter } from "next/navigation";

const NAV_ITEMS = [
  { label: "Dashboard",   href: "/dashboard",           icon: LayoutDashboard },
  { label: "Reports",     href: "/dashboard/reports",   icon: FileText },
  { label: "Upload Scan", href: "/dashboard/scan",      icon: FileScan },
  { label: "Search",      href: "/dashboard/search",    icon: Search },
  { label: "Analytics",   href: "/dashboard/analytics", icon: BarChart3 },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, clearAuth } = useAuthStore();
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
    clearAuth();
    router.push("/login");
  };

  return (
    <aside
      className="fixed left-0 top-0 h-screen w-60 flex flex-col z-30"
      style={{
        backgroundColor: "var(--sidebar-bg)",
        borderRight: "1px solid var(--sidebar-border)",
      }}
    >
      {/* Logo */}
      <div
        className="h-14 flex items-center justify-center px-5"
        style={{ borderBottom: "1px solid var(--sidebar-border)" }}
      >
        <Image
          src="/radsight-logo.png"
          alt="RadSight"
          width={130}
          height={36}
          className="object-contain"
          priority
        />
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        <p
          className="text-[10px] uppercase tracking-widest px-3 mb-2"
          style={{ color: "var(--sidebar-text-muted)" }}
        >
          Navigation
        </p>
        {NAV_ITEMS.map(({ label, href, icon: Icon }) => {
          const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={cn("sidebar-item", active && "active")}
            >
              <Icon size={15} />
              <span className="flex-1">{label}</span>
              {active && <ChevronRight size={11} style={{ opacity: 0.5 }} />}
            </Link>
          );
        })}
      </nav>

      {/* User section */}
      <div
        className="px-3 py-5 space-y-1"
        style={{ borderTop: "1px solid var(--sidebar-border)" }}
      >
        <div className="flex items-center gap-3 px-3 py-2.5 mb-1 rounded-lg"
          style={{ background: "var(--sidebar-item-active-bg, rgba(255,255,255,0.06))" }}>
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold shrink-0"
            style={{
              backgroundColor: "var(--sidebar-avatar-bg)",
              color: "var(--sidebar-avatar-text)",
            }}
          >
            {user?.full_name?.[0] ?? "U"}
          </div>
          <div className="flex-1 min-w-0">
            <p
              className="text-sm font-semibold truncate"
              style={{ color: "var(--sidebar-text-primary)" }}
            >
              {user?.full_name ?? "User"}
            </p>
            <p
              className="text-xs capitalize mt-0.5"
              style={{ color: "var(--sidebar-text-muted)" }}
            >
              {user?.role ?? "—"}
            </p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="sidebar-item w-full hover:!text-rose-400 hover:!bg-rose-400/10"
        >
          <LogOut size={15} />
          <span className="text-sm">Sign out</span>
        </button>
      </div>
    </aside>
  );
}
