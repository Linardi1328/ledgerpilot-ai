import { LegalPage } from "@/components/legal/LegalPage";

export default function CookiesPage() {
  return <LegalPage title="Cookie Policy" summary={<p>The audited LedgerPilot frontend does not intentionally include advertising pixels or behavioural analytics. It therefore does not display a non-essential cookie banner in the current development build.</p>} sections={[
    { title: "Necessary application state", body: <p>Authentication, security, tenant/client context, or framework infrastructure may use necessary session mechanisms in a deployed environment. Those mechanisms must be limited to what is needed to deliver the requested application functionality.</p> },
    { title: "No marketing tracking in the audited frontend", body: <p>No Google Analytics, Meta Pixel, Hotjar, Mixpanel, PostHog, or similar behavioural advertising tracker was found in the audited frontend code.</p> },
    { title: "Future analytics or embeds", body: <p>Before enabling non-essential analytics, advertising, cross-site tracking, or third-party embeds, the deployment must assess whether prior consent is required for its users. Where it is, those technologies must remain off until a valid choice is recorded and changeable.</p> },
    { title: "Browser controls", body: <p>Browsers allow users to clear or block cookies and site storage. Blocking necessary session technology may prevent authenticated or tenant-scoped features from working.</p> },
  ]} />;
}
