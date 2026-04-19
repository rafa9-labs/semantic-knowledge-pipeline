"use client";

import { ReactNode } from "react";

interface PaywallGateProps {
  children: ReactNode;
  feature?: string;
}

export function PaywallGate({ children, feature = "this content" }: PaywallGateProps) {
  return <>{children}</>;
}
