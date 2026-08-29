"use client";

import React, { createContext, useContext, useState } from "react";
import {
  SYNTHETIC_CLIENT_A_ID,
  SYNTHETIC_CLIENT_B_ID,
  SYNTHETIC_FIRM_ID,
} from "../mock/fixtures";

export interface ClientEntity {
  id: string;
  name: string;
  code: string;
  isDemo: boolean;
}

export interface FirmEntity {
  id: string;
  name: string;
  isDemo: boolean;
}

interface ClientContextType {
  activeFirm: FirmEntity;
  activeClient: ClientEntity;
  availableClients: ClientEntity[];
  setActiveClientId: (id: string) => void;
}

const DEFAULT_FIRM: FirmEntity = {
  id: SYNTHETIC_FIRM_ID,
  name: "Acme Accounting LLP [Demo]",
  isDemo: true,
};

const DEFAULT_CLIENTS: ClientEntity[] = [
  {
    id: SYNTHETIC_CLIENT_A_ID,
    name: "Alpha Trading Sdn Bhd [Demo]",
    code: "ALPHA-MY",
    isDemo: true,
  },
  {
    id: SYNTHETIC_CLIENT_B_ID,
    name: "Beta Logistics Bhd [Demo]",
    code: "BETA-MY",
    isDemo: true,
  },
];

const ClientContext = createContext<ClientContextType | undefined>(undefined);

export function ClientProvider({ children }: { children: React.ReactNode }) {
  const [activeFirm] = useState<FirmEntity>(DEFAULT_FIRM);
  const [availableClients] = useState<ClientEntity[]>(DEFAULT_CLIENTS);
  const [activeClientId, setActiveClientId] = useState<string>(SYNTHETIC_CLIENT_A_ID);

  const activeClient =
    availableClients.find((c) => c.id === activeClientId) || availableClients[0];

  return (
    <ClientContext.Provider
      value={{
        activeFirm,
        activeClient,
        availableClients,
        setActiveClientId,
      }}
    >
      {children}
    </ClientContext.Provider>
  );
}

export function useClientContext(): ClientContextType {
  const context = useContext(ClientContext);
  if (!context) {
    throw new Error("useClientContext must be used within a ClientProvider");
  }
  return context;
}
