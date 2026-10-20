import { NavLink } from "react-router";

import { useAuth } from "../features/auth/AuthContext";

interface NavItem {
  to: string;
  label: string;
}

const USER_LINKS: NavItem[] = [
  { to: "/kyc/status", label: "KYC status" },
  { to: "/kyc/upload", label: "Upload ID" },
];

const ADMIN_LINKS: NavItem[] = [{ to: "/admin/kyc", label: "KYC review" }];

function linkClass({ isActive }: { isActive: boolean }): string {
  return isActive ? "font-semibold text-indigo-700" : "text-slate-600 hover:text-slate-900";
}

export function NavBar() {
  const { user, logout } = useAuth();
  const links = user === null ? [] : user.role === "admin" ? [...USER_LINKS, ...ADMIN_LINKS] : USER_LINKS;

  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex max-w-4xl flex-wrap items-center gap-4 px-4 py-3">
        <span className="mr-auto font-semibold text-indigo-700">Digital Wallet eKYC</span>
        {links.map((link) => (
          <NavLink key={link.to} to={link.to} className={linkClass}>
            {link.label}
          </NavLink>
        ))}
        {user === null ? (
          <>
            <NavLink to="/login" className={linkClass}>
              Log in
            </NavLink>
            <NavLink to="/register" className={linkClass}>
              Register
            </NavLink>
          </>
        ) : (
          <>
            <span className="text-sm text-slate-500">{user.full_name}</span>
            <button type="button" onClick={logout} className="text-slate-600 hover:text-slate-900">
              Log out
            </button>
          </>
        )}
      </nav>
    </header>
  );
}
