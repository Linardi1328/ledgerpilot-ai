"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { Permission, Principal, Role } from "@/types/roles";
import { DEV_USERS, SYNTHETIC_FIRM_ID } from "../mock/fixtures";
import { mockDataStore } from "../mock/mock-client";
import { checkLiveness, fetchContext } from "../api/context";
import { defaultApiClient } from "../api/client";

export type OperatingMode = "live" | "mock";
export type BackendConnectionStatus = "connected" | "connecting" | "unavailable" | "unauthenticated";

interface AuthContextType {
  mode: OperatingMode;
  setMode: (mode: OperatingMode) => void;
  role: Role;
  setRole: (role: Role) => void;
  principal: Principal | null;
  devSubject: string;
  firmId: string;
  connectionStatus: BackendConnectionStatus;
  refreshContext: () => Promise<void>;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<OperatingMode>("mock");
  const [role, setRoleState] = useState<Role>(Role.ACCOUNTANT);
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<BackendConnectionStatus>("connecting");
  const [isLoading, setIsLoading] = useState(true);

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

    // Live Mode: Probe backend liveness and context
    try {
      await checkLiveness(defaultApiClient);
      const contextData = await fetchContext(defaultApiClient, {
        devSubject,
        firmId,
      });

      const parsedPrincipal: Principal = {
        user_id: contextData.user_id,
        firm_id: contextData.firm_id,
        membership_id: contextData.membership_id,
        role: contextData.role as Role,
        permissions: contextData.permissions as Permission[],
        authorized_client_ids: contextData.authorized_client_ids,
      };

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
      }
      setConnectionStatus("unavailable");
      // Fall back to mock principal for graceful inspection while backend is offline
      setPrincipal(mockDataStore.getPrincipal(role));
    } finally {
      setIsLoading(false);
    }
  }, [mode, role, devSubject, firmId]);

  useEffect(() => {
    refreshContext();
  }, [refreshContext]);

  const setRole = (newRole: Role) => {
    setRoleState(newRole);
    mockDataStore.setRole(newRole);
  };

  return (
    <AuthContext.Provider
      value={{
        mode,
        setMode,
        role,
        setRole,
        principal,
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
