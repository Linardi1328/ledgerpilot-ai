"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { Permission, Principal, Role } from "@/types/roles";
import { DEV_USERS, SYNTHETIC_FIRM_ID } from "../mock/fixtures";
import { mockDataStore } from "../mock/mock-client";
import { checkLiveness, fetchContext, validateContextResponse } from "../api/context";
import { defaultApiClient } from "../api/client";

export type OperatingMode = "live" | "mock";
export type BackendConnectionStatus =
  | "connected"
  | "connecting"
  | "unavailable"
  | "unauthenticated"
  | "invalid_context";

interface AuthContextType {
  mode: OperatingMode;
  setMode: (mode: OperatingMode) => void;
  role: Role; // Selected simulator role in the UI header
  setRole: (role: Role) => void;
  principal: Principal | null; // Authoritative principal
  effectiveRole: Role | null; // Verified server-authoritative role in live mode, simulator role in mock mode
  effectivePrincipal: Principal | null; // Verified principal (null in live mode when unauthenticated/unavailable/invalid)
  devSubject: string;
  firmId: string;
  connectionStatus: BackendConnectionStatus;
  refreshContext: () => Promise<void>;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<OperatingMode>("mock");
  const [role, setRoleState] = useState<Role>(Role.ACCOUNTANT);
  const [principal, setPrincipal] = useState<Principal | null>(() => mockDataStore.getPrincipal(Role.ACCOUNTANT));
  const [connectionStatus, setConnectionStatus] = useState<BackendConnectionStatus>("connected");
  const [isLoading, setIsLoading] = useState(false);

  // Active Dev Subject & Firm ID
  const devUser = Object.values(DEV_USERS).find((u) => u.role === role) || DEV_USERS.accountant;
  const devSubject = devUser.subject;
  const firmId = SYNTHETIC_FIRM_ID;

  const refreshContext = useCallback(async () => {
    setIsLoading(true);
    if (mode === "mock") {
      mockDataStore.setRole(role);
      const p = mockDataStore.getPrincipal(role);
      setPrincipal(p);
      setConnectionStatus("connected");
      setIsLoading(false);
      return;
    }

    // Live Mode: Must fail closed. Only valid /api/v1/context establishes active principal.
    try {
      await checkLiveness(defaultApiClient);
      const rawContextData = await fetchContext(defaultApiClient, {
        devSubject,
        firmId,
      });

      // Runtime schema validation
      const parsedPrincipal = validateContextResponse(rawContextData);

      setPrincipal(parsedPrincipal);
      setConnectionStatus("connected");
    } catch (err: unknown) {
      if (err && typeof err === "object" && "code" in err) {
        const code = (err as { code: string }).code;
        if (code === "unauthenticated" || code === "forbidden") {
          setConnectionStatus("unauthenticated");
          setPrincipal(null);
          setIsLoading(false);
          return;
        }
        if (code === "invalid_context_payload") {
          setConnectionStatus("invalid_context");
          setPrincipal(null);
          setIsLoading(false);
          return;
        }
      }
      setConnectionStatus("unavailable");
      // FAIL CLOSED: Never fall back to a mock principal in live mode!
      setPrincipal(null);
    } finally {
      setIsLoading(false);
    }
  }, [mode, role, devSubject, firmId]);

  useEffect(() => {
    refreshContext();
  }, [refreshContext]);

  const setRole = (newRole: Role) => {
    setRoleState(newRole);
    if (mode === "mock") {
      mockDataStore.setRole(newRole);
      setPrincipal(mockDataStore.getPrincipal(newRole));
    }
  };

  const setMode = (newMode: OperatingMode) => {
    setModeState(newMode);
    if (newMode === "mock") {
      mockDataStore.setRole(role);
      setPrincipal(mockDataStore.getPrincipal(role));
      setConnectionStatus("connected");
    } else {
      setPrincipal(null);
      setConnectionStatus("connecting");
    }
  };

  // Normalized Authoritative Principal & Role
  const effectivePrincipal: Principal | null = principal;
  const effectiveRole: Role | null = principal ? principal.role : null;

  return (
    <AuthContext.Provider
      value={{
        mode,
        setMode,
        role,
        setRole,
        principal,
        effectiveRole,
        effectivePrincipal,
        devSubject,
        firmId,
        connectionStatus,
        refreshContext,
        isLoading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
